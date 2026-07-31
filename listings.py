import os
import uuid

from flask import (
    Blueprint, render_template, request, current_app, abort, redirect,
    url_for, flash, g,
)
from werkzeug.utils import secure_filename

from db import get_db
from helpers import login_required

bp = Blueprint("listings", __name__)

PER_PAGE = 12

SORT_OPTIONS = {
    "newest": ("l.created_at DESC", "Newest first"),
    "price_asc": ("l.price_cents ASC", "Price: low to high"),
    "price_desc": ("l.price_cents DESC", "Price: high to low"),
}

ALLOWED_IMAGE_EXT = {"jpg", "jpeg", "png", "webp", "gif"}


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


def _parse_price_to_cents(text):
    """'1,299.99' → 129999. Returns None on invalid input."""
    if not text:
        return None
    cleaned = text.replace("$", "").replace(",", "").strip()
    try:
        dollars = float(cleaned)
    except ValueError:
        return None
    if dollars < 0:
        return None
    return int(round(dollars * 100))


def _save_uploaded_image(file_storage):
    """Save an uploaded image file and return its public URL, or None.

    Returns a tuple (url, error_message). On no file, both are None.
    """
    if not file_storage or not file_storage.filename:
        return None, None

    original = secure_filename(file_storage.filename)
    if "." not in original:
        return None, "Image filename must include an extension."

    ext = original.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        return None, "Image must be a JPG, PNG, WebP, or GIF."

    unique = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, unique))
    return f"/static/img/uploads/{unique}", None


def _delete_image_file(url):
    """Remove a previously-saved upload from disk; ignore anything external."""
    if not url or not url.startswith("/static/img/uploads/"):
        return
    filename = url.rsplit("/", 1)[-1]
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


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
    if listing["status"] not in ("active", "pending_review", "sold"):
        if g.user is None or g.user["id"] != listing["seller_id"]:
            abort(404)

    thread = db.execute(
        "SELECT m.*, u.name AS sender_name "
        "FROM messages m JOIN users u ON m.sender_id = u.id "
        "WHERE m.listing_id = ? ORDER BY m.created_at ASC",
        (listing_id,),
    ).fetchall()

    return render_template("detail.html", listing=listing, thread=thread)


# ── Create ─────────────────────────────────────────────────────

@bp.route("/listing/new", methods=("GET", "POST"))
@login_required
def new():
    db = get_db()
    categories = _categories_for_nav()

    if request.method == "POST":
        return _save_listing(existing=None, categories=categories)

    return render_template(
        "listings/form.html",
        categories=categories,
        listing=None,
        form_title="List a new asset",
        submit_label="Publish listing",
        form_action=url_for("listings.new"),
    )


# ── Edit ───────────────────────────────────────────────────────

@bp.route("/listing/<int:listing_id>/edit", methods=("GET", "POST"))
@login_required
def edit(listing_id):
    db = get_db()
    listing = db.execute(
        "SELECT l.*, c.grp AS category_grp "
        "FROM listings l JOIN categories c ON l.category_id = c.id "
        "WHERE l.id = ?",
        (listing_id,),
    ).fetchone()

    if listing is None:
        abort(404)
    # server-side ownership check — never trust the client
    if listing["seller_id"] != g.user["id"]:
        abort(403)

    categories = _categories_for_nav()

    if request.method == "POST":
        return _save_listing(existing=listing, categories=categories)

    return render_template(
        "listings/form.html",
        categories=categories,
        listing=listing,
        form_title="Edit listing",
        submit_label="Save changes",
        form_action=url_for("listings.edit", listing_id=listing_id),
    )


# ── Remove ─────────────────────────────────────────────────────

@bp.route("/listing/<int:listing_id>/remove", methods=("POST",))
@login_required
def remove(listing_id):
    db = get_db()
    listing = db.execute(
        "SELECT id, seller_id, status FROM listings WHERE id = ?", (listing_id,)
    ).fetchone()

    if listing is None:
        abort(404)
    # server-side ownership check — never trust the client
    if listing["seller_id"] != g.user["id"]:
        abort(403)

    if listing["status"] == "sold":
        flash("Sold listings can't be removed.", "error")
        return redirect(url_for("dashboard.index"))

    db.execute(
        "UPDATE listings SET status = 'removed' WHERE id = ?", (listing_id,)
    )
    db.commit()
    flash("Listing removed.", "success")
    return redirect(url_for("dashboard.index"))


# ── Shared create/edit save ────────────────────────────────────

def _save_listing(existing, categories):
    """Validate the form and either INSERT or UPDATE the listing.

    `existing` is None on create, or a listing row on edit.
    """
    db = get_db()

    # --- collect ---
    category_id = request.form.get("category_id", type=int)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    price_raw = request.form.get("price", "").strip()
    platform = request.form.get("platform", "").strip()
    metric_label = request.form.get("metric_label", "").strip()
    metric_value = request.form.get("metric_value", "").strip()
    delivery_method = request.form.get("delivery_method", "").strip()
    attested = request.form.get("seller_attested") == "1"
    remove_image = request.form.get("remove_image") == "1"

    # --- validate category ---
    category = None
    if category_id:
        category = db.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        ).fetchone()

    error = None
    if category is None:
        error = "Please choose a category."
    elif (category["grp"] == "social_account"
          and not current_app.config["ENABLE_SOCIAL_ACCOUNTS"]):
        error = "That category isn't available."
    elif not title:
        error = "Title is required."
    elif len(title) > 200:
        error = "Title must be 200 characters or fewer."
    elif not description:
        error = "Description is required."
    else:
        price_cents = _parse_price_to_cents(price_raw)
        if price_cents is None:
            error = "Please enter a valid price, e.g. 299 or 1499.99."
        elif price_cents == 0:
            error = "Price must be greater than zero."
        elif category["grp"] == "social_account" and not attested:
            error = "Please confirm the ownership attestation to continue."

    if error:
        flash(error, "error")
        # re-render the form with what they entered so nothing is lost
        submitted = {
            "category_id": category_id,
            "title": title,
            "description": description,
            "price": price_raw,
            "platform": platform,
            "metric_label": metric_label,
            "metric_value": metric_value,
            "delivery_method": delivery_method,
            "image_url": existing["image_url"] if existing else None,
            "seller_attested": attested,
        }
        return render_template(
            "listings/form.html",
            categories=categories,
            listing=submitted,
            form_title=("Edit listing" if existing else "List a new asset"),
            submit_label=("Save changes" if existing else "Publish listing"),
            form_action=(
                url_for("listings.edit", listing_id=existing["id"])
                if existing else url_for("listings.new")
            ),
        )

    # --- image handling ---
    image_url = existing["image_url"] if existing else None
    upload = request.files.get("image")
    new_url, image_error = _save_uploaded_image(upload)
    if image_error:
        flash(image_error, "error")
        return redirect(request.url)
    if new_url:
        # replacing — clean up the old file if any
        if existing and existing["image_url"]:
            _delete_image_file(existing["image_url"])
        image_url = new_url
    elif remove_image and existing and existing["image_url"]:
        _delete_image_file(existing["image_url"])
        image_url = None

    # --- status routing based on category group ---
    if existing is None:
        status = "pending_review" if category["grp"] == "social_account" else "active"
    else:
        status = existing["status"]
        old_grp = existing["category_grp"]
        new_grp = category["grp"]
        if new_grp == "social_account" and old_grp != "social_account":
            # newly a social account — needs re-review
            status = "pending_review"
        elif new_grp != "social_account" and old_grp == "social_account":
            # no longer a social account — clear the pending state
            if status == "pending_review":
                status = "active"

    # --- write ---
    if existing is None:
        cur = db.execute(
            "INSERT INTO listings (seller_id, category_id, title, description, "
            "price_cents, image_url, platform, metric_label, metric_value, "
            "delivery_method, status, seller_attested) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                g.user["id"], category["id"], title, description, price_cents,
                image_url, platform or None, metric_label or None,
                metric_value or None, delivery_method or None, status,
                1 if attested else 0,
            ),
        )
        listing_id = cur.lastrowid
        db.commit()
        if status == "pending_review":
            flash(
                "Listing submitted for review. It'll appear in browse once an "
                "admin approves it.",
                "success",
            )
        else:
            flash("Listing published.", "success")
    else:
        db.execute(
            "UPDATE listings SET category_id=?, title=?, description=?, "
            "price_cents=?, image_url=?, platform=?, metric_label=?, "
            "metric_value=?, delivery_method=?, status=?, seller_attested=? "
            "WHERE id = ?",
            (
                category["id"], title, description, price_cents, image_url,
                platform or None, metric_label or None, metric_value or None,
                delivery_method or None, status, 1 if attested else 0,
                existing["id"],
            ),
        )
        listing_id = existing["id"]
        db.commit()
        flash("Listing updated.", "success")

    return redirect(url_for("listings.detail", listing_id=listing_id))
