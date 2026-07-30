# Design prompt — paste into Claude Code

> Use this **before Phase 3**. It replaces the "Design direction" section of the original spec.

---

Stop building features. We're fixing the visual design first, so every page built from here inherits it.

Read the current templates and stylesheet, then rebuild the design system from scratch to the spec below. Put **every** token in `static/css/style.css` as CSS custom properties on `:root`. No inline styles, no per-page stylesheets, no hardcoded hex values anywhere in the templates — if I change a variable in one place, the whole site changes.

## The idea behind the design

This site sells digital assets, and every asset here is really a set of numbers: subscribers, monthly revenue, visitors, price. So **figures are the design**. Numbers get set in a monospace face with tabular alignment, treated like entries in a ledger — precise, aligned, unembellished. Everything else stays quiet so the numbers carry the page.

Minimal here means precision, not emptiness. Get spacing and alignment exactly right rather than adding decoration.

## Colour

```css
--paper:        #FFFFFF;   /* page background */
--surface:      #F5F6F8;   /* cards, inputs, raised areas */
--ink:          #16181D;   /* primary text */
--ink-muted:    #6C727F;   /* secondary text, labels */
--line:         #E3E6EA;   /* borders, dividers */
--accent:       #0E6E5C;   /* primary actions, links, active states */
--accent-hover: #0A5546;
--accent-soft:  #E6F2EF;   /* accent backgrounds, active nav pill */
--warn:         #B4690E;   /* pending review status */
--warn-soft:    #FDF3E4;
--danger:       #C0362C;   /* errors, destructive actions */
--danger-soft:  #FBECEA;
```

Rules:
- The accent appears on primary buttons, links, and active states. **Nowhere else.** No accent-coloured headings, no accent borders on cards, no gradients anywhere.
- Never use pure black or pure grey text — always `--ink` or `--ink-muted`.
- Status badges use the soft background with the matching solid colour as text.

If the green doesn't suit, the only swap I'll accept is `--accent: #1B3FD8` with `--accent-hover: #152FA6` and `--accent-soft: #EAEEFC`. Don't invent a third option.

## Type

Load from Google Fonts, with system fallbacks so nothing breaks offline:

- **Display** (`--font-display`): `'Space Grotesk', sans-serif` — headings and the logo only
- **Body** (`--font-body`): `'Inter', system-ui, sans-serif` — all body text, buttons, labels, inputs
- **Figures** (`--font-mono`): `'IBM Plex Mono', ui-monospace, monospace` — prices, metrics, dates, order IDs

Scale — use these and nothing between them:

```css
--text-xs:   12px;   /* labels, badges, captions */
--text-sm:   14px;   /* secondary text, form help */
--text-base: 16px;   /* body */
--text-lg:   20px;   /* card titles, section headings */
--text-xl:   28px;   /* page titles */
--text-2xl:  40px;   /* hero only */
```

Weights: 400 body, 500 UI/buttons, 600 headings. Never 700+, never 300.

Line height: 1.5 body, 1.2 headings, 1 on figures.

**All numbers get `font-variant-numeric: tabular-nums`** so digits align in columns. This matters — it's the whole idea.

Uppercase labels (`--text-xs`, weight 500, `letter-spacing: 0.06em`) for eyebrows and field labels. Sentence case everywhere else — never uppercase a button or heading.

## Spacing, radius, elevation

- 4px base scale: `4, 8, 12, 16, 24, 32, 48, 64, 96`. Nothing off-scale.
- Radius: `--radius-sm: 6px` (inputs, badges), `--radius: 10px` (cards, buttons). Nothing fully rounded except avatars.
- **No box-shadows on resting elements.** Depth comes from `1px solid var(--line)`. A shadow appears only on hover, and only on cards: `0 2px 12px rgba(22, 24, 29, 0.06)`.
- Max content width 1140px, centred, 24px side padding (16px under 640px).

## Components

**Buttons** — 40px tall, 16px horizontal padding, `--text-sm`, weight 500, `--radius`.
- Primary: `--accent` background, white text. Hover `--accent-hover`.
- Secondary: `--paper` background, `--line` border, `--ink` text. Hover: border darkens to `--ink-muted`.
- Ghost: no border, `--ink-muted` text, hover `--ink`.
- Never more than one primary button visible in any single view.

**Inputs** — 40px tall, `--surface` background, `1px solid var(--line)`, `--radius-sm`. On focus: background goes `--paper`, border goes `--accent`, plus a 3px `--accent-soft` ring. Labels sit above in the uppercase label style. Error state: `--danger` border with the message directly below in `--text-sm`.

**Listing card — this is the signature element, get it right.**

Structure, top to bottom:
1. 16:9 image area. If there's no image, fill with `--surface` and centre the category icon at 32px in `--ink-muted`. No broken image icons, ever.
2. Category name in the uppercase label style, `--ink-muted`.
3. Title, `--text-lg`, weight 600, display font, clamped to 2 lines with ellipsis.
4. A hairline `--line` divider.
5. A bottom row, `display: flex; justify-content: space-between; align-items: baseline`:
   - **Left:** the metric — value in mono at `--text-lg` `--ink`, and beneath it the metric label in the uppercase label style `--ink-muted`. (e.g. `41,200` / `SUBSCRIBERS`)
   - **Right:** the price in mono at `--text-lg` weight 500, right-aligned, `--ink`.

Both figures use tabular numerals so cards in a grid line up vertically with each other. That alignment is the point — don't break it.

Card is `--paper` with a `--line` border. On hover: border goes `--ink-muted`, the card lifts `translateY(-2px)`, and the hover shadow appears. 150ms ease-out.

**Status badges** — `--text-xs`, weight 500, 4px/10px padding, `--radius-sm`, soft background + solid text. Active → accent. Pending review → warn. Sold → muted grey. Removed → danger.

**Navigation** — 64px tall, `--paper`, 1px bottom border. Logo left in display font weight 600. Links centre in `--text-sm` `--ink-muted`; the active one gets `--ink` and an `--accent-soft` pill. Right side: "Sell an asset" as a primary button, then the account menu. Under 768px collapse to a hamburger.

## Auth pages specifically

These are what I'm looking at right now and they're the weakest screens. Rebuild them as a **centred single card**, 420px max width, vertically centred, `--paper` card with `--line` border on a `--surface` page background.

Inside: logo at top, page title in `--text-xl` display, one line of `--text-sm` `--ink-muted` explaining what happens next, then the fields, then a full-width primary button, then a `--text-sm` link to the opposite action ("New here? Create an account").

No hero image, no marketing copy, no two-column split. Just the card.

## Quality floor — not optional

- Responsive down to 360px. Listing grid: 3 columns → 2 at 900px → 1 at 640px.
- Visible focus rings on every interactive element: 2px `--accent` outline, 2px offset. Never `outline: none` without a replacement.
- Wrap all transitions in `@media (prefers-reduced-motion: no-preference)`.
- Text contrast at WCAG AA minimum.
- Every form input has a real `<label>`, not just a placeholder.
- Every image has meaningful alt text.

## Copy

Rewrite any placeholder text you find. Buttons name the action that happens: "Create account", "List your asset", "Buy now". Empty states invite an action — "No listings yet. Be the first to list something." not "No results found." Errors say what went wrong and how to fix it — "That email is already registered. Try logging in instead." not "Invalid input."

## What to do now

Restyle only what exists so far — the base template, nav, auth pages, and any home page. Build the listing card styles too, even though the cards aren't used until Phase 3, so the system is complete before we get there.

When you're done, run the app and describe what each page looks like now. Then wait — don't start Phase 3 until I've looked at it.
