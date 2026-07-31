from flask import (
    Blueprint, render_template, redirect, url_for, flash, abort,
)

from db import get_db
from helpers import admin_required

bp = Blueprint("admin", __name__)


@bp.route("/admin")
@admin_required
def index():
    db = get_db()

    stats = {
        "users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "active_listings": db.execute(
            "SELECT COUNT(*) FROM listings WHERE status = 'active'"
        ).fetchone()[0],
        "orders": db.execute(
            "SELECT COUNT(*) FROM orders WHERE status IN ('paid', 'completed')"
        ).fetchone()[0],
        # Total volume is the sum of paid/completed order amounts, in cents.
        "volume_cents": db.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM orders "
            "WHERE status IN ('paid', 'completed')"
        ).fetchone()[0],
    }

    queue = db.execute(
        "SELECT l.*, c.name AS category_name, c.slug AS category_slug, "
        "c.icon AS category_icon, u.name AS seller_name "
        "FROM listings l "
        "JOIN categories c ON l.category_id = c.id "
        "JOIN users u ON l.seller_id = u.id "
        "WHERE l.status = 'pending_review' "
        "ORDER BY l.created_at ASC",
    ).fetchall()

    return render_template("admin/index.html", stats=stats, queue=queue)


@bp.route("/admin/listing/<int:listing_id>/approve", methods=("POST",))
@admin_required
def approve(listing_id):
    _set_status(listing_id, "active", "Listing approved and published.")
    return redirect(url_for("admin.index"))


@bp.route("/admin/listing/<int:listing_id>/reject", methods=("POST",))
@admin_required
def reject(listing_id):
    _set_status(listing_id, "removed", "Listing rejected and removed.")
    return redirect(url_for("admin.index"))


def _set_status(listing_id, new_status, message):
    """Move a pending_review listing to *new_status*; ignore anything else."""
    db = get_db()
    listing = db.execute(
        "SELECT id, status FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()

    if listing is None:
        abort(404)
    if listing["status"] != "pending_review":
        flash("That listing is no longer awaiting review.", "warning")
        return

    db.execute(
        "UPDATE listings SET status = ? WHERE id = ?", (new_status, listing_id)
    )
    db.commit()
    flash(message, "success")
