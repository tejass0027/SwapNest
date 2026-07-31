from flask import (
    Blueprint, render_template, request, current_app, abort,
)

from db import get_db

bp = Blueprint("listings", __name__)

PER_PAGE = 12

SORT_OPTIONS = {
    "newest": ("l.created_at DESC", "Newest first"),
    "price_asc": ("l.price_cents ASC", "Price: low to high"),
    "price_desc": ("l.price_cents DESC", "Price: high to low"),
}


def _categories_for_nav():
    """Return categories visible under the current feature-flag setting."""
    db = get_db()
    if current_app.config["ENABLE_SOCIAL_ACCOUNTS"]:
        return db.execute(
            "SELECT * FROM categories ORDER BY grp, name"
        ).fetchall()
    return db.execute(
        "SELECT * FROM categories WHERE grp = 'digital' ORDER BY name"
    ).fetchall()


# ── Home page ──────────────────────────────────────────────────

@bp.route("/")
def home():
    db = get_db()
    categories = _categories_for_nav()

    featured = db.execute(
        "SELECT l.*, c.name AS category_name, c.slug AS category_slug, "
        "c.icon AS category_icon, c.grp AS category_grp, u.name AS seller_name "
        "FROM listings l "
        "JOIN categories c ON l.category_id = c.id "
        "JOIN users u ON l.seller_id = u.id "
        "WHERE l.status = 'active' "
        "ORDER BY l.created_at DESC LIMIT 6",
    ).fetchall()

    return render_template(
        "home.html", categories=categories, featured=featured,
    )


# ── Browse ─────────────────────────────────────────────────────

@bp.route("/browse")
def browse():
    db = get_db()
    social_enabled = current_app.config["ENABLE_SOCIAL_ACCOUNTS"]
    categories = _categories_for_nav()

    # --- collect filter params ---
    category_slug = request.args.get("category", "")
    group = request.args.get("group", "")
    q = request.args.get("q", "").strip()
    price_min = request.args.get("price_min", "", type=str).strip()
    price_max = request.args.get("price_max", "", type=str).strip()
    sort_key = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)

    if sort_key not in SORT_OPTIONS:
        sort_key = "newest"
    if page < 1:
        page = 1

    # --- build query ---
    clauses = ["l.status = 'active'"]
    params = []

    if not social_enabled:
        clauses.append("c.grp = 'digital'")

    if category_slug:
        clauses.append("c.slug = ?")
        params.append(category_slug)
    elif group in ("digital", "social_account"):
        clauses.append("c.grp = ?")
        params.append(group)

    if q:
        clauses.append("(l.title LIKE ? OR l.description LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])

    if price_min:
        try:
            clauses.append("l.price_cents >= ?")
            params.append(int(float(price_min) * 100))
        except ValueError:
            pass

    if price_max:
        try:
            clauses.append("l.price_cents <= ?")
            params.append(int(float(price_max) * 100))
        except ValueError:
            pass

    where = " AND ".join(clauses)
    order = SORT_OPTIONS[sort_key][0]

    # count
    count = db.execute(
        f"SELECT COUNT(*) FROM listings l "
        f"JOIN categories c ON l.category_id = c.id "
        f"WHERE {where}",
        params,
    ).fetchone()[0]

    total_pages = max(1, -(-count // PER_PAGE))
    if page > total_pages:
        page = total_pages

    offset = (page - 1) * PER_PAGE

    listings = db.execute(
        f"SELECT l.*, c.name AS category_name, c.slug AS category_slug, "
        f"c.icon AS category_icon, c.grp AS category_grp, u.name AS seller_name "
        f"FROM listings l "
        f"JOIN categories c ON l.category_id = c.id "
        f"JOIN users u ON l.seller_id = u.id "
        f"WHERE {where} "
        f"ORDER BY {order} "
        f"LIMIT ? OFFSET ?",
        params + [PER_PAGE, offset],
    ).fetchall()

    # active category object for the heading
    active_category = None
    if category_slug:
        active_category = db.execute(
            "SELECT * FROM categories WHERE slug = ?", (category_slug,)
        ).fetchone()

    return render_template(
        "browse.html",
        listings=listings,
        categories=categories,
        active_category=active_category,
        count=count,
        page=page,
        total_pages=total_pages,
        sort_key=sort_key,
        sort_options=SORT_OPTIONS,
        # pass filters back so the template can preserve them
        f_category=category_slug,
        f_group=group,
        f_q=q,
        f_price_min=price_min,
        f_price_max=price_max,
    )


# ── Listing detail ─────────────────────────────────────────────

@bp.route("/listing/<int:listing_id>")
def detail(listing_id):
    db = get_db()
    social_enabled = current_app.config["ENABLE_SOCIAL_ACCOUNTS"]

    listing = db.execute(
        "SELECT l.*, c.name AS category_name, c.slug AS category_slug, "
        "c.icon AS category_icon, c.grp AS category_grp, "
        "u.name AS seller_name, u.bio AS seller_bio, "
        "u.is_verified AS seller_verified, u.created_at AS seller_since "
        "FROM listings l "
        "JOIN categories c ON l.category_id = c.id "
        "JOIN users u ON l.seller_id = u.id "
        "WHERE l.id = ?",
        (listing_id,),
    ).fetchone()

    if listing is None:
        abort(404)

    if listing["category_grp"] == "social_account" and not social_enabled:
        abort(404)

    # don't expose draft/removed to non-owners
    from flask import g
    if listing["status"] not in ("active", "pending_review", "sold"):
        if g.user is None or g.user["id"] != listing["seller_id"]:
            abort(404)

    return render_template("detail.html", listing=listing)
