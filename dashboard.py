from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g,
)

from db import get_db
from helpers import login_required

bp = Blueprint("dashboard", __name__)


@bp.route("/dashboard")
@login_required
def index():
    db = get_db()
    uid = g.user["id"]

    my_listings = db.execute(
        "SELECT l.*, c.name AS category_name, c.slug AS category_slug, "
        "c.icon AS category_icon "
        "FROM listings l JOIN categories c ON l.category_id = c.id "
        "WHERE l.seller_id = ? "
        "ORDER BY l.created_at DESC",
        (uid,),
    ).fetchall()

    orders_received = db.execute(
        "SELECT o.*, l.title AS listing_title, l.id AS listing_id, "
        "b.name AS buyer_name "
        "FROM orders o "
        "JOIN listings l ON o.listing_id = l.id "
        "JOIN users b ON o.buyer_id = b.id "
        "WHERE o.seller_id = ? "
        "ORDER BY o.created_at DESC",
        (uid,),
    ).fetchall()

    orders_placed = db.execute(
        "SELECT o.*, l.title AS listing_title, l.id AS listing_id, "
        "l.delivery_method AS delivery_method, "
        "s.name AS seller_name "
        "FROM orders o "
        "JOIN listings l ON o.listing_id = l.id "
        "JOIN users s ON o.seller_id = s.id "
        "WHERE o.buyer_id = ? "
        "ORDER BY o.created_at DESC",
        (uid,),
    ).fetchall()

    # Every message posted on one of my listings — the seller's inbox.
    messages_received = db.execute(
        "SELECT m.*, u.name AS sender_name, l.title AS listing_title, "
        "l.id AS listing_id "
        "FROM messages m "
        "JOIN listings l ON m.listing_id = l.id "
        "JOIN users u ON m.sender_id = u.id "
        "WHERE l.seller_id = ? AND m.sender_id != ? "
        "ORDER BY m.created_at DESC LIMIT 20",
        (uid, uid),
    ).fetchall()

    return render_template(
        "dashboard/index.html",
        my_listings=my_listings,
        orders_received=orders_received,
        orders_placed=orders_placed,
        messages_received=messages_received,
    )


@bp.route("/dashboard/profile", methods=("GET", "POST"))
@login_required
def profile():
    db = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        bio = request.form.get("bio", "").strip()

        if not name:
            flash("Name can't be empty.", "error")
            return render_template("dashboard/profile.html", name=name, bio=bio)
        if len(name) > 120:
            flash("Name must be 120 characters or fewer.", "error")
            return render_template("dashboard/profile.html", name=name, bio=bio)

        db.execute(
            "UPDATE users SET name = ?, bio = ? WHERE id = ?",
            (name, bio or None, g.user["id"]),
        )
        db.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("dashboard.profile"))

    return render_template(
        "dashboard/profile.html",
        name=g.user["name"],
        bio=g.user["bio"] or "",
    )
