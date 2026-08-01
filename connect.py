"""Seller-side Stripe Connect onboarding.

Sellers need their own connected Stripe Express account before checkout
can pay them (see checkout.py's destination-charge transfer_data). This
blueprint creates that account, sends the seller through Stripe's hosted
onboarding, and reports their status back on the dashboard.

Every route here requires a real Stripe key — there is nothing to onboard
into in demo mode, so each view checks DEMO_MODE first and bails out with
a clear message rather than calling the API with an empty key.
"""

import stripe
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, g

from db import get_db
from helpers import login_required

bp = Blueprint("connect", __name__, url_prefix="/dashboard/payouts")


def _create_or_get_account():
    """Return the seller's Stripe Express account id, creating one if needed."""
    if g.user["stripe_account_id"]:
        return g.user["stripe_account_id"]

    account = stripe.Account.create(
        type="express",
        email=g.user["email"],
        capabilities={"transfers": {"requested": True}},
    )
    db = get_db()
    db.execute(
        "UPDATE users SET stripe_account_id = ? WHERE id = ?",
        (account.id, g.user["id"]),
    )
    db.commit()
    return account.id


def _start_onboarding():
    """Create (or resume) the seller's account and return a fresh Stripe
    onboarding URL. Account links expire after a few minutes, so both the
    initial "Connect" click and Stripe's refresh_url callback funnel here."""
    account_id = _create_or_get_account()
    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=url_for("connect.refresh", _external=True),
        return_url=url_for("connect.return_to_dashboard", _external=True),
        type="account_onboarding",
    )
    return link.url


@bp.route("/")
@login_required
def index():
    if current_app.config["DEMO_MODE"]:
        return render_template("dashboard/payouts.html", demo_mode=True, account=None)

    account = None
    if g.user["stripe_account_id"]:
        try:
            account = stripe.Account.retrieve(g.user["stripe_account_id"])
        except stripe.error.StripeError:
            account = None

    return render_template("dashboard/payouts.html", demo_mode=False, account=account)


@bp.route("/connect", methods=("POST",))
@login_required
def start():
    if current_app.config["DEMO_MODE"]:
        flash("Stripe isn't configured for this deployment yet — set STRIPE_SECRET_KEY to enable payouts.", "error")
        return redirect(url_for("connect.index"))

    try:
        onboarding_url = _start_onboarding()
    except stripe.error.StripeError:
        flash("We couldn't start Stripe onboarding. Please try again.", "error")
        return redirect(url_for("connect.index"))

    return redirect(onboarding_url)


@bp.route("/return")
@login_required
def return_to_dashboard():
    # Stripe lands the seller here after onboarding (complete or not) —
    # index() re-checks live status, so there's nothing to do but go look.
    return redirect(url_for("connect.index"))


@bp.route("/refresh")
@login_required
def refresh():
    # Stripe sends the seller here if their onboarding link expired
    # mid-flow. Same demo-mode guard as start(), just via GET since this
    # is Stripe's own redirect, not a form submission.
    if current_app.config["DEMO_MODE"]:
        return redirect(url_for("connect.index"))

    try:
        onboarding_url = _start_onboarding()
    except stripe.error.StripeError:
        flash("We couldn't refresh Stripe onboarding. Please try again.", "error")
        return redirect(url_for("connect.index"))

    return redirect(onboarding_url)
