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
  - `esc(s)` — HTML-escapes `&`, `<`, `>`, `"`, `'`; use on all user-entered strings in `innerHTML` contexts
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

## Asset class badges

Asset class labels are displayed as color-coded badges everywhere they appear in tables (dashboard holdings, investments all-holdings, data holdings, rebalance sells). Badge style:

```js
`<span class="badge" style="background:${COLORS[h.asset_class]||'#506070'}26;color:${COLORS[h.asset_class]||'#506070'};">${CLASS_LABELS[h.asset_class]||h.asset_class}</span>`
```

The `26` suffix on the hex color is `0x26 = 15%` opacity — tinted background matching the donut chart color.

## `loadData()` pattern

The `/data` page fetches all APIs in a single `Promise.all`. If any fetch fails, none of the `build*` functions run. Add new data sources to the `Promise.all` array and destructure the result.

## CSV import tab pattern

CSV import functionality lives inside its corresponding tab as a second card below the main form — never as a standalone tab. See the Snapshot tab in `data.html` as the reference implementation.

## Category dropdowns and transaction inbox

All transaction category fields use `<select>` populated by `buildCatOpts(cats, selectedVal)` (defined in `base.html`). This preserves orphaned category values — ones present on a transaction but no longer in `budget_categories` — to prevent silent data loss on edit.

Transaction categories are optional. Blank values are normalized to `uncategorized` by the API, and Data → Transactions exposes an `Uncategorized` filter plus row selection for bulk category assignment.

## Hash-based tab nav on `/data`

`showTab(id)` updates `history.replaceState` with `#id`. On load: `loadData().then(() => { if (hash) showTab(hash); })` activates the correct tab. Direct links like `/data#transactions` work correctly. Transactions also supports the `#transactions:uncategorized` subview, used by the Budget page callout.

## Drift color semantics

`drift-pos` (over-allocated) = red. `drift-neg` (under-allocated) = accent/blue. `drift-zero` = green. This is intentionally inverted from the naive reading — being over-allocated in an asset class is the alert condition.

## Conditional KPI tiles

The "Other Assets" tile is hidden by default (`style="display:none"`) and shown in JS only when `dash.other_assets > 0`. When shown, the KPI row grid is also widened:

```js
if ((dash.other_assets || 0) > 0) {
  document.getElementById('kpi-other-card').style.display = '';
  document.getElementById('kpi-row').style.gridTemplateColumns = 'repeat(6, 1fr)';
}
```

The matching NW chart dataset and chart-legend item follow the same conditional — checked against `history.some(h => (h.other_assets || 0) > 0)` in `renderNWChart()`. Use this pattern for any future metric that should only appear when data is present rather than showing as `—` permanently.

## Number inputs

Browser spinners are hidden globally via `style.css` (`-webkit-appearance: none` + `-moz-appearance: textfield`).

## XSS safety rule

Any user-entered string rendered inside a template literal that is assigned to `innerHTML` must go through `esc(s)`. Numbers, dates, enum values (direction, account type), and computed values (fmt output, percentages) do not need escaping.
