import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db
from helpers import safe_redirect_url

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user:
        return redirect(url_for("listings.home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = None
        if not name:
            error = "Name is required."
        elif not email or not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        else:
            db = get_db()
            existing = db.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                error = "An account with that email already exists."

        if error:
            flash(error, "error")
            return render_template("auth/register.html", name=name, email=email)

        db = get_db()
        cur = db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        session.clear()
        session["user_id"] = cur.lastrowid
        flash("Welcome to SwapNest! Your account has been created.", "success")
        return redirect(url_for("listings.home"))

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user:
        return redirect(url_for("listings.home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html", email=email)

        session.clear()
        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name']}!", "success")

        next_url = safe_redirect_url(request.args.get("next"))
        return redirect(next_url or url_for("listings.home"))

    return render_template("auth/login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("listings.home"))
