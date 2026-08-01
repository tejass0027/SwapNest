import os


def _bool_env(value, default):
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "./marketplace.db")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    PLATFORM_FEE_PERCENT = int(os.environ.get("PLATFORM_FEE_PERCENT", "5"))
    ENABLE_SOCIAL_ACCOUNTS = _bool_env(os.environ.get("ENABLE_SOCIAL_ACCOUNTS"), True)
    SITE_NAME = os.environ.get("SITE_NAME", "SwapNest")

    # No Stripe key configured means there's no way to actually charge a
    # card, so the app runs in demo mode: purchases complete instantly and
    # are clearly labelled as fake.
    DEMO_MODE = not STRIPE_SECRET_KEY

    # Cookie hardening. SECURE defaults to False so local dev over plain
    # http:// keeps working — browsers silently drop "Secure" cookies on
    # a non-HTTPS origin, which would otherwise break every login. Set
    # SESSION_COOKIE_SECURE=true once the app is served over HTTPS.
    SESSION_COOKIE_SECURE = _bool_env(os.environ.get("SESSION_COOKIE_SECURE"), False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
