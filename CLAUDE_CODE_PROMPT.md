# Build prompt — paste into Claude Code

> Copy everything below the line into Claude Code in an empty directory.
> Build it in phases; don't accept "done" until each phase actually runs.

---

Build a digital assets marketplace called **Ledger** — a web app where sellers list digital assets and buyers purchase them.

## Stack (use exactly this — do not substitute)

- **Backend:** Flask (Python 3.11+), blueprints, application-factory pattern
- **Database:** SQLite via the standard-library `sqlite3` module. Raw SQL in `schema.sql`. No ORM.
- **Templates:** Jinja2, server-rendered. No React, no SPA, no build step.
- **CSS:** One hand-written stylesheet using CSS custom properties. No Tailwind, no Bootstrap.
- **JS:** Vanilla only, minimal, progressive enhancement. No framework.
- **Auth:** Flask sessions + `werkzeug.security` password hashing.
- **Payments:** Stripe Checkout (hosted redirect), called via `requests` against the REST API. Do not add the `stripe` SDK.

Dependencies are limited to: `Flask`, `Werkzeug`, `requests`. Ask before adding anything else.

## What it sells

Two category groups:

**`digital`** — always enabled:
- Software & SaaS
- Mobile Apps
- Websites & Domains
- Templates & Source Code
- Digital Services

**`social_account`** — behind the `ENABLE_SOCIAL_ACCOUNTS` config flag:
- YouTube Channels
- Instagram Accounts
- TikTok Accounts
- X / Twitter Accounts
- Facebook Pages

The flag must genuinely hide the group everywhere — nav, browse filters, the listing-create form's category dropdown, and search results — not just visually.

## Data model

Write this as `schema.sql`. Prices are **integer cents** everywhere. Never use floats for money.

- **users** — `id`, `name`, `email` (unique), `password_hash`, `is_admin`, `is_verified`, `bio`, `created_at`
- **categories** — `id`, `name`, `slug` (unique), `grp` (`'digital'` | `'social_account'`), `icon`
- **listings** — `id`, `seller_id`, `category_id`, `title`, `description`, `price_cents`, `currency`, `image_url`, `platform`, `metric_label`, `metric_value`, `delivery_method`, `status`, `seller_attested`, `created_at`
- **orders** — `id`, `listing_id`, `buyer_id`, `seller_id`, `amount_cents`, `currency`, `status`, `stripe_session_id`, `created_at`
- **messages** — `id`, `listing_id`, `sender_id`, `body`, `created_at`

Listing status flow: `draft` → `pending_review` (social accounts only) → `active` → `sold` / `removed`
Order status flow: `pending` → `paid` → `completed` / `cancelled`

Add indexes on `listings.category_id`, `listings.status`, `orders.buyer_id`, `orders.seller_id`, `messages.listing_id`. Enable `PRAGMA foreign_keys = ON` on every connection.

## File layout

```
app.py          config.py       db.py         helpers.py
schema.sql      seed.py         requirements.txt
auth.py         listings.py     dashboard.py  checkout.py   admin.py
templates/      static/css/     static/js/    static/img/
```

## Phase 1 — Foundation

`config.py` reading from environment with these defaults: `SECRET_KEY=dev-secret-change-me`, `DATABASE_PATH=./marketplace.db`, `STRIPE_SECRET_KEY=""`, `PLATFORM_FEE_PERCENT=5`, `ENABLE_SOCIAL_ACCOUNTS=true`, `SITE_NAME=Ledger`. Derive `DEMO_MODE = not STRIPE_SECRET_KEY`.

`db.py` with `get_db()` using Flask's `g`, `close_db()` registered on teardown, and `init_db()` that executes `schema.sql`.

`app.py` as an application factory: registers blueprints, loads the logged-in user into `g` before each request, injects `site_name` / `demo_mode` / `social_accounts_enabled` / `current_user` into template context, registers a `usd` Jinja filter that formats cents as `1,299.00`.

`seed.py` that wipes and recreates the database, inserts all 10 categories, 4 demo users (one admin), and ~8 sample listings spread across categories — including two social-account listings left in `pending_review` so the admin queue has something in it. Print the demo logins at the end.

**Checkpoint:** `python seed.py` runs clean and creates the DB.

## Phase 2 — Auth

`auth.py`: register, log in, log out.

- Validate email format and uniqueness; minimum 8-character password
- Hash with `generate_password_hash`, verify with `check_password_hash`
- On login failure, give one generic message — never reveal whether the email exists
- `@login_required` and `@admin_required` decorators in `helpers.py`
- Honour a `?next=` redirect parameter after login, but only accept relative paths (reject anything with a scheme or host — open-redirect guard)

**Checkpoint:** register a new user, log out, log back in.

## Phase 3 — Listings

`listings.py`:

- `/` — home: hero, category grid, featured active listings
- `/browse` — all active listings with filters: category, group, price min/max, search across title and description, and sort by newest / price ascending / price descending. Filters must combine, and must survive in the querystring when paginating.
- `/listing/<id>` — detail page: full description, price, seller card, key metrics, delivery method, buy button, and the message thread
- `/listing/new` — create (login required)
- `/listing/<id>/edit` — edit (owner only — verify ownership server-side, not just by hiding the button)

Build search and filters with **parameterised queries**. Never build SQL by string concatenation.

**Social account listings specifically:**
- The create form shows an ownership/eligibility attestation checkbox that must be ticked to submit
- On submit they get `status='pending_review'`, not `'active'`
- The detail page shows a visible notice that account transfers may violate the platform's terms and that the buyer should do their own due diligence

**Checkpoint:** create a listing in each group, confirm the social one lands in `pending_review` and does not appear in browse.

## Phase 4 — Checkout

`checkout.py`:

- `POST /checkout/<listing_id>` — create an order with `status='pending'`. **Re-read the price from the database.** Never take an amount from the form.
- Block buying your own listing. Block buying anything not `active`.
- **Demo mode** (no Stripe key): mark the order `paid` immediately, redirect to a success page with an obvious demo badge so it's unmistakable that no money moved.
- **Live mode:** create a Stripe Checkout Session via `POST https://api.stripe.com/v1/checkout/sessions` using HTTP basic auth with the secret key as username. Pass `client_reference_id` and `metadata[order_id]`. Redirect to the returned `url`.
- `/checkout/success` and `/checkout/cancel` pages
- `POST /webhook/stripe` — mark the order `paid` on `checkout.session.completed`. **Verify the webhook signature** against `STRIPE_WEBHOOK_SECRET` using HMAC-SHA256 and reject anything unsigned or stale. Do not mark orders paid based on the success-page redirect alone.
- Show the platform fee breakdown at checkout: item price, fee, seller payout.

**Checkpoint:** complete a purchase in demo mode; the order shows up in both dashboards.

## Phase 5 — Dashboards & admin

`dashboard.py`:
- Seller view: my listings with status badges, edit/remove, orders received
- Buyer view: orders placed with status and delivery instructions
- Profile edit: name and bio

`admin.py` (admin only):
- Review queue of `pending_review` listings with approve / reject actions
- Approve sets `status='active'`; reject sets `status='removed'`
- Basic stats: user count, active listings, total order volume

**Checkpoint:** log in as admin, approve a pending listing, confirm it appears in browse.

## Phase 6 — Messaging

Threaded messages on the listing detail page between buyer and seller. Login required to post. Show sender name and timestamp. Sellers can see all threads on their listings from the dashboard.

## Design direction

Modern and minimal — that's the brief, so honour it. Minimal means precision, not emptiness: get spacing, type scale, and alignment exactly right rather than adding decoration.

- **Palette:** neutral base (white / near-black text), one restrained accent used only for primary actions and active states, plus muted semantic colours for status badges. Pick a specific accent and use it consistently — avoid warm-clay/terracotta and acid-green, they read as generic AI-design defaults.
- **Type:** two faces maximum. A characterful display face for headings used sparingly, a highly legible face for body and UI. Set a clear scale (something like 12 / 14 / 16 / 20 / 28 / 40) and stick to it.
- **Layout:** generous whitespace, a consistent max content width, a card grid for listings that stays readable at every breakpoint.
- **Signature element:** the listing card. It's the thing users see most, so make it the memorable piece — a clear price treatment, one prominent metric (subscribers / MRR / visitors), category and status badges, and a restrained hover state.
- **Motion:** hover and focus transitions only. Respect `prefers-reduced-motion`.

Quality floor, no exceptions: responsive to 360px, visible keyboard focus rings, semantic HTML, labelled form inputs, alt text on images, colour contrast at WCAG AA.

Write real copy, not lorem ipsum. Buttons say what happens: "List your asset", "Buy now", "Send message". Empty states invite an action rather than just saying "nothing here". Errors say what went wrong and how to fix it.

## Security requirements — non-negotiable

- Parameterised SQL everywhere
- Passwords hashed, never stored or logged in plain text
- Authorisation checked server-side on every mutating route — hiding a button is not access control
- Prices re-read from the DB at checkout, never trusted from the client
- Stripe webhook signatures verified
- Jinja2 autoescaping left on; no `|safe` on user-supplied content
- No secrets committed — provide `.env.example`, and add `.env` and `*.db` to `.gitignore`

## Deliverables

Working app, plus `requirements.txt`, `.env.example`, `.gitignore`, and a `README.md` covering setup, config, and demo logins.

## How to work

Build phase by phase. After each phase, actually run the app and verify the checkpoint before moving on. Tell me what you verified. If a requirement here seems wrong or you'd suggest a better approach, say so before implementing rather than silently substituting.
