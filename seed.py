"""Wipes and recreates the database, then loads demo data.

Run with: python seed.py
"""

from werkzeug.security import generate_password_hash

from app import create_app
from db import get_db, init_db

CATEGORIES = [
    # (name, slug, group, icon)
    ("Software & SaaS", "software-saas", "digital", "\U0001F4BB"),
    ("Mobile Apps", "mobile-apps", "digital", "\U0001F4F1"),
    ("Websites & Domains", "websites-domains", "digital", "\U0001F310"),
    ("Templates & Source Code", "templates-source-code", "digital", "\U0001F9E9"),
    ("Digital Services", "digital-services", "digital", "\U0001F6E0"),
    ("YouTube Channels", "youtube-channels", "social_account", "▶"),
    ("Instagram Accounts", "instagram-accounts", "social_account", "\U0001F4F8"),
    ("TikTok Accounts", "tiktok-accounts", "social_account", "\U0001F3B5"),
    ("X / Twitter Accounts", "x-twitter-accounts", "social_account", "X"),
    ("Facebook Pages", "facebook-pages", "social_account", "\U0001F4D8"),
]

# (name, email, password, is_admin, is_verified, bio)
USERS = [
    ("SwapNest Admin", "admin@ledger.test", "admin123", 1, 1,
     "Keeping the marketplace tidy."),
    ("Alex Rivera", "alex@ledger.test", "password123", 0, 1,
     "Full-stack dev flipping side projects."),
    ("Sam Okafor", "sam@ledger.test", "password123", 0, 0,
     "New seller, first listing incoming."),
    ("Priya Desai", "priya@ledger.test", "password123", 0, 1,
     "Growth marketer, runs a few niche channels on the side."),
]

# (seller_email, category_slug, title, description, price_cents,
#  platform, metric_label, metric_value, delivery_method, status, seller_attested)
LISTINGS = [
    (
        "alex@ledger.test", "software-saas",
        "Invoicely — subscription invoicing SaaS",
        "A working invoicing SaaS with Stripe billing, 40 paying customers, "
        "and clean Next.js/Postgres codebase. Includes source, domain, and "
        "customer handoff support for 30 days.",
        450000, "Web", "MRR", "$1,200/mo",
        "Codebase transfer + domain + customer handoff call", "active", 0,
    ),
    (
        "alex@ledger.test", "mobile-apps",
        "FocusTimer — iOS & Android productivity app",
        "A Pomodoro-style focus timer app, live on both app stores with "
        "3,400 downloads. React Native source included, App Store listing "
        "transferred to buyer.",
        180000, "iOS / Android", "Downloads", "3,400",
        "Source zip + store listing transfer", "active", 0,
    ),
    (
        "priya@ledger.test", "websites-domains",
        "minimalstudio.io — ready-to-launch portfolio site",
        "A polished agency portfolio site and matching domain, built with "
        "static HTML/CSS. Includes hosting config notes and a short intro "
        "video walkthrough.",
        65000, "Web", "Monthly visitors", "9,000",
        "Domain transfer + site files via email", "active", 0,
    ),
    (
        "sam@ledger.test", "templates-source-code",
        "Next.js SaaS Starter Kit",
        "Auth, billing, and dashboard scaffolding for Next.js, ready to "
        "fork for your next SaaS idea. MIT-licensed once purchased, GitHub "
        "repo invite included.",
        9900, "Web", "GitHub stars", "210",
        "GitHub repo invite", "active", 0,
    ),
    (
        "priya@ledger.test", "digital-services",
        "Landing page copywriting (1 project)",
        "One full landing page rewrite: headline, subhead, feature copy, "
        "and CTA, delivered in a Google Doc within 5 business days.",
        25000, "Any", "Projects completed", "38",
        "Delivered via Google Doc", "active", 0,
    ),
    (
        "sam@ledger.test", "websites-domains",
        "recipevault.app — starter recipe site",
        "A simple recipe-sharing site with a small existing domain, sold "
        "as-is with basic SEO already in place.",
        32000, "Web", "Domain age", "3 years",
        "Domain transfer + site files via email", "active", 0,
    ),
    (
        "alex@ledger.test", "youtube-channels",
        "Tech review channel, 42K subscribers",
        "A tech review channel with 4 years of consistent uploads and an "
        "engaged audience. Selling due to a shift in focus to a new project.",
        800000, "YouTube", "Subscribers", "42,000",
        "Ownership transfer via YouTube Studio", "pending_review", 1,
    ),
    (
        "priya@ledger.test", "instagram-accounts",
        "Travel photography account, 18K followers",
        "A travel photography account with steady engagement and a niche, "
        "loyal following built up over two years.",
        350000, "Instagram", "Followers", "18,200",
        "Ownership transfer via Instagram business settings",
        "pending_review", 1,
    ),
]


def run():
    app = create_app()
    with app.app_context():
        init_db()
        db = get_db()

        category_ids = {}
        for name, slug, grp, icon in CATEGORIES:
            cur = db.execute(
                "INSERT INTO categories (name, slug, grp, icon) VALUES (?, ?, ?, ?)",
                (name, slug, grp, icon),
            )
            category_ids[slug] = cur.lastrowid

        user_ids = {}
        for name, email, password, is_admin, is_verified, bio in USERS:
            cur = db.execute(
                "INSERT INTO users (name, email, password_hash, is_admin, is_verified, bio) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (name, email, generate_password_hash(password), is_admin, is_verified, bio),
            )
            user_ids[email] = cur.lastrowid

        for (seller_email, category_slug, title, description, price_cents,
             platform, metric_label, metric_value, delivery_method, status,
             seller_attested) in LISTINGS:
            db.execute(
                "INSERT INTO listings "
                "(seller_id, category_id, title, description, price_cents, "
                "platform, metric_label, metric_value, delivery_method, "
                "status, seller_attested) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_ids[seller_email], category_ids[category_slug], title,
                    description, price_cents, platform, metric_label,
                    metric_value, delivery_method, status, seller_attested,
                ),
            )

        db.commit()

    print("Database wiped and reseeded.\n")
    print("Demo logins:")
    for name, email, password, is_admin, is_verified, bio in USERS:
        role = "admin" if is_admin else "seller"
        print(f"  {email:<20} {password:<14} ({role})")


if __name__ == "__main__":
    run()
