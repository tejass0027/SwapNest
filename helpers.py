import functools
from urllib.parse import urlparse

from flask import g, redirect, url_for, flash, request


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
            return redirect(url_for("index"))
        return view(**kwargs)
    return wrapped


def safe_redirect_url(target):
    """Return *target* only if it is a safe, relative URL — block open redirects."""
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    return target
