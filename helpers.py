import functools
from urllib.parse import urlparse

import stripe
from flask import g, redirect, url_for, flash, request

from db import get_db


def login_required(view):
    """Redirect to login if the user is not signed in."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    """Redirect non-admins away — checks server-side, not just UI."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if not g.user["is_admin"]:
            flash("You don't have permission to access that page.", "error")
            return redirect(url_for("listings.home"))
        return view(**kwargs)
    return wrapped


def fee_breakdown(price_cents, fee_percent):
    """Split a price into the platform fee and the seller's payout.

    All integer cents — the fee is floored so the platform never over-charges
    by a rounding cent, and the payout takes the remainder.
    """
    fee_cents = price_cents * fee_percent // 100
    payout_cents = price_cents - fee_cents
    return fee_cents, payout_cents


def seller_payouts_ready(seller_id):
    """True if this seller has a Stripe Connect account that can receive
    transfers right now.

    Only meaningful in live mode — callers must check DEMO_MODE first, since
    calling this without a real Stripe key configured would just fail.
    Returns False (no API call) if the seller hasn't started onboarding.
    """
    db = get_db()
    row = db.execute(
        "SELECT stripe_account_id FROM users WHERE id = ?", (seller_id,)
    ).fetchone()
    if not row or not row["stripe_account_id"]:
        return False
    try:
        account = stripe.Account.retrieve(row["stripe_account_id"])
    except stripe.error.StripeError:
        return False
    # Stripe's Account object has no .get() (see the note in checkout.py's
    # webhook handler) — check the key exists before subscripting it.
    return bool(account["payouts_enabled"]) if "payouts_enabled" in account else False


def safe_redirect_url(target):
    """Return *target* only if it is a safe, relative URL — block open redirects."""
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    return target
