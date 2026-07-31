from flask import (
    Blueprint, request, redirect, url_for, flash, g, abort,
)

from db import get_db
from helpers import login_required

bp = Blueprint("messages", __name__)

MAX_BODY = 2000


@bp.route("/listing/<int:listing_id>/message", methods=("POST",))
@login_required
def post(listing_id):
    db = get_db()
    listing = db.execute(
        "SELECT id, status, seller_id FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()

    if listing is None:
        abort(404)

    # Only allow messaging on listings a user could actually see. Drafts and
    # removed listings are hidden from everyone but their owner.
    if listing["status"] not in ("active", "pending_review", "sold"):
        if g.user["id"] != listing["seller_id"]:
            abort(404)

    body = request.form.get("body", "").strip()
    if not body:
        flash("Write a message before sending.", "error")
        return redirect(url_for("listings.detail", listing_id=listing_id) + "#messages")
    if len(body) > MAX_BODY:
        flash(f"Messages must be {MAX_BODY} characters or fewer.", "error")
        return redirect(url_for("listings.detail", listing_id=listing_id) + "#messages")

    db.execute(
        "INSERT INTO messages (listing_id, sender_id, body) VALUES (?, ?, ?)",
        (listing_id, g.user["id"], body),
    )
    db.commit()
    flash("Message sent.", "success")
    return redirect(url_for("listings.detail", listing_id=listing_id) + "#messages")
