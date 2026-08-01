import stripe
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g,
    current_app, abort,
)

from db import get_db
from helpers import login_required, fee_breakdown, seller_payouts_ready

bp = Blueprint("checkout", __name__)


def _load_active_listing_for_purchase(listing_id):
    """Fetch a listing and enforce that the current user may buy it.

    Returns the listing row, or aborts / flashes + returns None with a
    redirect target. Callers handle the redirect.
    """
    db = get_db()
    listing = db.execute(
        "SELECT l.*, c.name AS category_name, c.slug AS category_slug, "
        "c.icon AS category_icon "
        "FROM listings l JOIN categories c ON l.category_id = c.id "
        "WHERE l.id = ?",
        (listing_id,),
    ).fetchone()

    if listing is None:
        abort(404)
    return listing


def _purchase_error(listing):
    """Return a flash message if the current user can't buy this listing."""
    if listing["status"] != "active":
        return "This listing isn't available for purchase."
    if listing["seller_id"] == g.user["id"]:
        return "You can't buy your own listing."
    # In demo mode nothing real is ever transferred, so a seller's Connect
    # status is irrelevant. In live mode, block the purchase rather than
    # take a buyer's money with nowhere real to send the seller's share.
    if not current_app.config["DEMO_MODE"] and not seller_payouts_ready(listing["seller_id"]):
        return "This seller hasn't finished setting up payouts yet. Check back soon."
    return None


# ── Review page ────────────────────────────────────────────────

@bp.route("/checkout/<int:listing_id>")
@login_required
def review(listing_id):
    listing = _load_active_listing_for_purchase(listing_id)

    error = _purchase_error(listing)
    if error:
        flash(error, "error")
        return redirect(url_for("listings.detail", listing_id=listing_id))

    fee_percent = current_app.config["PLATFORM_FEE_PERCENT"]
    fee_cents, payout_cents = fee_breakdown(listing["price_cents"], fee_percent)

    return render_template(
        "checkout/review.html",
        listing=listing,
        fee_percent=fee_percent,
        fee_cents=fee_cents,
        payout_cents=payout_cents,
    )


# ── Create order + start payment ───────────────────────────────

@bp.route("/checkout/<int:listing_id>", methods=("POST",))
@login_required
def start(listing_id):
    db = get_db()
    listing = _load_active_listing_for_purchase(listing_id)

    error = _purchase_error(listing)
    if error:
        flash(error, "error")
        return redirect(url_for("listings.detail", listing_id=listing_id))

    # Re-read the price from the DB — never trust an amount from the client.
    amount_cents = listing["price_cents"]
    currency = listing["currency"] or "usd"

    cur = db.execute(
        "INSERT INTO orders (listing_id, buyer_id, seller_id, amount_cents, "
        "currency, status) VALUES (?, ?, ?, ?, ?, 'pending')",
        (listing["id"], g.user["id"], listing["seller_id"], amount_cents, currency),
    )
    order_id = cur.lastrowid
    db.commit()

    # ── Demo mode: no Stripe key, so complete instantly (no money moves). ──
    if current_app.config["DEMO_MODE"]:
        _mark_order_paid(order_id)
        return redirect(url_for("checkout.success", order_id=order_id, demo=1))

    # ── Live mode: hand off to Stripe Checkout, split at the source. ──
    seller = db.execute(
        "SELECT stripe_account_id FROM users WHERE id = ?", (listing["seller_id"],)
    ).fetchone()
    fee_percent = current_app.config["PLATFORM_FEE_PERCENT"]
    fee_cents, _ = fee_breakdown(amount_cents, fee_percent)

    success_url = url_for("checkout.success", order_id=order_id, _external=True)
    success_url += "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = url_for("checkout.cancel", order_id=order_id, _external=True)

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(order_id),
            metadata={"order_id": str(order_id)},
            line_items=[{
                "quantity": 1,
                "price_data": {
                    "currency": currency,
                    "unit_amount": amount_cents,
                    "product_data": {"name": listing["title"]},
                },
            }],
            # Destination charge: the full amount is charged to the buyer,
            # Stripe keeps application_fee_amount for the platform and
            # transfers the rest straight to the seller's connected account.
            payment_intent_data={
                "application_fee_amount": fee_cents,
                "transfer_data": {"destination": seller["stripe_account_id"]},
            },
        )
    except stripe.error.StripeError:
        db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
        db.commit()
        flash("We couldn't reach the payment provider. Please try again.", "error")
        return redirect(url_for("listings.detail", listing_id=listing_id))

    db.execute(
        "UPDATE orders SET stripe_session_id = ? WHERE id = ?",
        (session.id, order_id),
    )
    db.commit()

    return redirect(session.url)


# ── Success / cancel ───────────────────────────────────────────

@bp.route("/checkout/success")
@login_required
def success(order_id=None):
    order_id = request.args.get("order_id", type=int)
    order = _load_own_order(order_id)
    if order is None:
        abort(404)

    demo = request.args.get("demo") == "1"
    return render_template("checkout/success.html", order=order, demo=demo)


@bp.route("/checkout/cancel")
@login_required
def cancel(order_id=None):
    order_id = request.args.get("order_id", type=int)
    order = _load_own_order(order_id)
    if order is None:
        abort(404)
    return render_template("checkout/cancel.html", order=order)


def _load_own_order(order_id):
    """Fetch an order joined to its listing, only if it belongs to the buyer."""
    if not order_id:
        return None
    db = get_db()
    order = db.execute(
        "SELECT o.*, l.title AS listing_title, l.id AS listing_id, "
        "c.slug AS category_slug, c.icon AS category_icon, "
        "u.name AS seller_name "
        "FROM orders o "
        "JOIN listings l ON o.listing_id = l.id "
        "JOIN categories c ON l.category_id = c.id "
        "JOIN users u ON o.seller_id = u.id "
        "WHERE o.id = ? AND o.buyer_id = ?",
        (order_id, g.user["id"]),
    ).fetchone()
    return order


# ── Payment completion (shared by demo + webhook) ──────────────

def _mark_order_paid(order_id):
    """Mark an order paid and its listing sold. Idempotent."""
    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if order is None or order["status"] == "paid":
        return
    db.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order_id,))
    db.execute(
        "UPDATE listings SET status = 'sold' WHERE id = ? AND status = 'active'",
        (order["listing_id"],),
    )
    db.commit()


# ── Stripe webhook ─────────────────────────────────────────────

@bp.route("/webhook/stripe", methods=("POST",))
def webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    secret = current_app.config["STRIPE_WEBHOOK_SECRET"]

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        # Never trust an unparseable, unsigned, or stale callback.
        abort(400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Stripe's deserialized event objects are typed Session/StripeObject
        # instances, not plain dicts — they support `in` and `[]` but have
        # no .get(), so missing keys must be checked explicitly.
        metadata = session["metadata"] if "metadata" in session else None
        order_id = metadata["order_id"] if metadata and "order_id" in metadata else None
        if not order_id and "client_reference_id" in session:
            order_id = session["client_reference_id"]
        if order_id:
            try:
                _mark_order_paid(int(order_id))
            except (ValueError, TypeError):
                pass

    return ("", 200)
