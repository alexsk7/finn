# Frontend Reference

## Stack

No build step. All JS is vanilla + Chart.js + Alpine.js (loaded from jsDelivr CDN in `base.html`).

## Template layer

- **`templates/base.html`** — shell (topbar + sidebar drawer + main area). Shared JS globals available on every page:
  - `COLORS` — asset class → hex color
  - `CLASS_LABELS` — asset class → display name
  - `fmt(n)` — currency formatter
  - `pct(n)` — percentage formatter
  - `clr(n)` — returns green/red CSS var based on sign
  - `buildCatOpts(cats, selectedVal)` — builds `<option>` HTML for category dropdowns, preserves orphaned values
  - `refreshPrices()` — triggers manual price refresh
  - `toggleSidebar()` — opens/closes the sidebar drawer
- Each page template defines `{% block content %}` and `{% block scripts %}`.
- Starlette 1.x requires keyword args: `TemplateResponse(request=req, name=tmpl, context={...})`.

## CSS custom properties

Defined in `static/style.css`:

`--bg`, `--bg2`, `--bg3`, `--border`, `--text`, `--text-dim`, `--text-head`, `--green`, `--red`, `--accent`, `--gap`, `--font`

## Responsive system

Named layout classes (`.layout-main-aside`, `.layout-alloc-row`, etc.) are defined in `style.css` and override to single-column at `@media (max-width: 768px)`. Every named layout's direct children get `min-width: 0`. Dense tables are wrapped in `.table-scroll` for horizontal scroll on mobile. The sidebar is a fixed drawer toggled by `body.sidebar-open`.

## Dashboard viewport fit

`#dash` is `display:flex; flex-direction:column; height:100%`. Content rows use `.dash-row` with `flex:1; min-height:0; grid-template-rows:1fr; align-items:stretch`. The `grid-template-rows:1fr` is the critical fix — without it, Chart.js canvases expand past their allocated height. Cards that must fill their cell use `.card-fill`. Right-side stacked columns use `.dash-col`.

## Inline table editing

Two `<tr>` per row: `#hrow-{id}` (display) and `#hrow-edit-{id}` (edit, hidden via `tr.hrow-edit { display:none }`). Toggle with `style.display = 'table-row'` — not `''`, which reverts to `display:none`. Used in holdings, budget categories, and transactions tables on `/data`.

## `loadData()` pattern

The `/data` page fetches all APIs in a single `Promise.all`. If any fetch fails, none of the `build*` functions run. Add new data sources to the `Promise.all` array and destructure the result.

## CSV import tab pattern

CSV import functionality lives inside its corresponding tab as a second card below the main form — never as a standalone tab. See the Snapshot tab in `data.html` as the reference implementation.

## Category dropdowns

All transaction category fields use `<select>` populated by `buildCatOpts(cats, selectedVal)` (defined in `base.html`). This preserves orphaned category values — ones present on a transaction but no longer in `budget_categories` — to prevent silent data loss on edit.

## Hash-based tab nav on `/data`

`showTab(id)` updates `history.replaceState` with `#id`. On load: `loadData().then(() => { if (hash) showTab(hash); })` activates the correct tab. Direct links like `/data#transactions` work correctly.

## Drift color semantics

`drift-pos` (over-allocated) = red. `drift-neg` (under-allocated) = accent/blue. `drift-zero` = green. This is intentionally inverted from the naive reading — being over-allocated in an asset class is the alert condition.

## Number inputs

Browser spinners are hidden globally via `style.css` (`-webkit-appearance: none` + `-moz-appearance: textfield`).
