# Ledger — Digital Assets Marketplace

A marketplace where people list and sell digital assets: SaaS products, mobile apps, websites and domains, code templates, digital services — and, optionally, social media accounts (YouTube, Instagram, TikTok, X, Facebook).

Buyers browse, filter, message sellers, and pay through Stripe Checkout. Sellers create listings, track orders, and hand over the asset after payment clears.

---

## Status

Early scaffold. Auth, listings, checkout, and admin review are specified but not all implemented. See `CLAUDE_CODE_PROMPT.md` for the full build spec.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Flask (Python 3.12) | Small, readable, easy to host anywhere |
| Database | SQLite | Zero setup; swap to Postgres later via SQLAlchemy |
| Templates | Jinja2, server-rendered | No build step, fast to iterate |
| Styling | Hand-written CSS, custom properties | Full control, no framework bloat |
| Payments | Stripe Checkout (hosted) | Card data never touches your server |
| Auth | Werkzeug password hashing + Flask sessions | Built in, no extra dependency |

No Node build step. No bundler. `pip install -r requirements.txt` and run.

---

## Getting started

```bash
# 1. Clone and enter the project
cd ledger

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create the database and load demo data
python seed.py

# 5. Run
python app.py
```

Open <http://localhost:5000>.

### Demo accounts

Created by `seed.py`:

| Email | Password | Role |
|---|---|---|
| `admin@ledger.test` | `admin123` | Admin — can approve/reject account listings |
| `alex@ledger.test` | `password123` | Seller (verified) |
| `sam@ledger.test` | `password123` | Seller (unverified) |
| `priya@ledger.test` | `password123` | Seller (verified) |

Change these before deploying anywhere public.

---

## Configuration

All config lives in `config.py` and reads from environment variables.

| Variable | Default | What it does |
|---|---|---|
| `SECRET_KEY` | `dev-secret-change-me` | Flask session signing key. **Must** be changed in production. |
| `DATABASE_PATH` | `./marketplace.db` | SQLite file location |
| `STRIPE_SECRET_KEY` | *(empty)* | Stripe secret key. If empty, app runs in **demo mode**. |
| `STRIPE_PUBLISHABLE_KEY` | *(empty)* | Stripe publishable key |
| `PLATFORM_FEE_PERCENT` | `5` | Marketplace cut, shown transparently at checkout |
| `ENABLE_SOCIAL_ACCOUNTS` | `true` | Set to `false` to hide the social-account category group entirely |
| `SITE_NAME` | `Ledger` | Display name used across the UI |

### Demo mode

With no `STRIPE_SECRET_KEY` set, purchases complete instantly without contacting Stripe. This lets you click through the entire buy flow before setting up a payment account. The checkout page shows a clear demo badge so it can't be mistaken for a real charge.

To go live:

```bash
export STRIPE_SECRET_KEY=sk_test_...
export STRIPE_PUBLISHABLE_KEY=pk_test_...
```

Use Stripe **test** keys first. Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

---

## Project structure

```
ledger/
├── app.py               # Application factory, blueprint registration
├── config.py            # Configuration and feature flags
├── db.py                # SQLite connection handling
├── schema.sql           # Database schema
├── seed.py              # Creates DB + demo data
├── helpers.py           # Auth decorators, formatting, Stripe calls
├── auth.py              # Register, log in, log out
├── listings.py          # Browse, search, detail, create, edit
├── dashboard.py         # Seller and buyer dashboards
├── checkout.py          # Order creation, Stripe session, webhooks
├── admin.py             # Review queue for account listings
├── templates/           # Jinja2 templates
└── static/
    ├── css/
    ├── js/
    └── img/
```

---

## Data model

- **users** — name, email, password hash, admin flag, verification flag
- **categories** — grouped into `digital` and `social_account`
- **listings** — seller, category, price in cents, metrics, delivery method, status
- **orders** — listing, buyer, seller, amount, status, Stripe session ID
- **messages** — buyer/seller conversation attached to a listing

Prices are stored as **integer cents**, never floats.

Listing statuses: `draft` → `pending_review` (social accounts only) → `active` → `sold` / `removed`.

---

## Important: social media account listings

Selling or transferring account ownership violates the terms of service of most major platforms — YouTube, Instagram, TikTok, X, and Facebook all prohibit it in some form. Accounts can be reclaimed or banned after transfer, leaving your buyer with nothing and your marketplace holding the dispute.

This category is also the single biggest fraud vector in this kind of business: stolen accounts, bot-inflated follower counts, and sellers who take payment and reclaim the account through the platform's own recovery flow.

The scaffold reflects that:

- The category group is behind a flag (`ENABLE_SOCIAL_ACCOUNTS`) so you can ship without it
- Account listings go to `pending_review` instead of publishing immediately
- Sellers must tick an ownership/eligibility attestation before submitting
- An admin queue exists to approve or reject before anything goes live

If you keep this category, you'll want, at minimum: real seller identity verification, funds held until the buyer confirms transfer (escrow), a written dispute process, and terms that make the seller liable for reclaimed accounts. Talk to a lawyer in your jurisdiction before taking real money — marketplace liability, payment regulations, and consumer protection rules vary a lot, and holding funds in escrow can trigger money-transmission licensing requirements in some places.

The general digital-assets categories carry none of this baggage and are a larger market anyway.

---

## Security checklist before going live

- [ ] Change `SECRET_KEY` to a long random value
- [ ] Change or delete all seeded demo accounts
- [ ] Set `session_cookie_secure = True` and serve over HTTPS
- [ ] Add CSRF protection on every form (`Flask-WTF`)
- [ ] Add rate limiting on login and registration (`Flask-Limiter`)
- [ ] Verify Stripe webhook signatures — never trust an unsigned callback
- [ ] Validate and re-encode uploaded images; serve them off a separate domain or CDN
- [ ] Escape all user-supplied content (Jinja2 autoescapes by default — don't use `|safe` on user input)
- [ ] Move from SQLite to Postgres before you have real traffic

---

## Roadmap

- [ ] Escrow: hold funds until buyer confirms delivery
- [ ] Seller identity verification (Stripe Identity)
- [ ] Ratings and reviews after completed orders
- [ ] Saved searches and email alerts
- [ ] Analytics for sellers (views, conversion)
- [ ] Dispute resolution flow

---

## License

Choose one before publishing. MIT is a reasonable default for a project you may open-source.
