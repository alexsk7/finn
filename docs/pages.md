# Pages and API Reference

## Page routes

| Route | Template | Description |
|---|---|---|
| `/` | `dashboard.html` | KPI tiles + sparklines, multi-line NW chart with period filters + projection overlay, allocation donut, cashflow, holdings (deduplicated by ticker), alerts, journal preview, market ticker strip |
| `/landing` | `landing.html` | Public-style product overview for finn's local-first ethos, feature set, support rationale, roadmap, and getting-started flow |
| `/investments` | `investments.html` | Full holdings table by account, allocation vs target, asset class performance |
| `/accounts` | `accounts.html` | Grouped account list; account names link to drill-down; liabilities shown as negative |
| `/accounts/{id}` | `account_detail.html` | Transaction history for one account, month separators, inline edit/delete; payoff projection for credit/loan accounts |
| `/real-estate` | `real_estate.html` | Properties, equity/LTV, amortization schedule, appreciation projection, capex log |
| `/tax` | `tax.html` | KPI tiles (unrealized total, YTD income, harvestable losses), YTD investment income by category, TLH candidates, full taxable gain/loss table |
| `/budget` | `budget.html` | Zero-based monthly budget planner with month navigation, planned vs actual income/expenses, variance, copy-month workflow, and uncategorized transaction callout |
| `/journal` | `journal.html` | Entry log with tags, milestones, inline edit/delete |
| `/rebalance` | `rebalance.html` | Tax-aware rebalance calculator; drift table, sell candidates, buy targets; optional new-cash input |
| `/data` | `data.html` | All data management — see tabs below |

## /data page tabs

Holdings | Accounts | Snapshot | Prices | Transactions | Real Estate | Allocation | Budget | Danger Zone

- **Holdings** — add form (with "Manual" checkbox for non-public tickers, auto-prefixes `M:`) + full table with two-row inline edit/delete and "manual" badge; CSV import card (Fidelity/Schwab/Vanguard formats, account selector)
- **Accounts** — add form (with opening balance + optional APR/min payment for credit/loan) + table with edit and delete
- **Snapshot** — per-account balance entry form + preview card; plus "Import Historical Snapshots" CSV import card
- **Prices** — last price per symbol, manual override inputs, refresh button. Manual holdings (`M:` prefix) are skipped by the Yahoo Finance refresh — update their prices here.
- **Transactions** — add form + recent transactions with two-row inline edit/delete, All/Uncategorized filters, row selection, bulk categorization, and "Import Transactions CSV" card. Category is optional; blank imports and manual entries become `uncategorized`.
- **Real Estate** — add property form + per-property value/mortgage update, linked loan account selector, delete
- **Allocation** — editable target % for all 8 asset classes, Save All
- **Budget** — add category form + two-row inline edit/delete table
- **Danger Zone** — full data reset; server requires `{"confirm":"RESET"}` in request body

## Dashboard features

- **KPI tiles**: Net Worth → Invested → Home Equity → Liquid Cash → Total Debt → Other Assets (conditional). Each tile shows current value, MoM % change, YTD % change, and an inline SVG sparkline. All values computed live. The "Other Assets" tile only appears when at least one `other`-type account has a non-zero balance; the KPI row expands to 6 columns automatically.
- **NW chart**: multi-line — Net Worth (blue, filled), Invested (green), Cash (yellow), Home Equity (purple), Other Assets (amber, conditional). Period filters: 30D, QTD, YTD, 1Y, 2Y, 5Y, MAX. "Proj" toggle adds a dashed 10-year projection line using CAGR from the visible history slice, anchored to current live NW. The Other Assets line and legend entry only appear when any snapshot has a non-zero `other_assets` value.
- **Market ticker strip**: scrolling marquee at bottom — major indices + all non-manual holding symbols with price and daily % change. Manual holdings (`is_manual=1`) are excluded from the strip.
- **Holdings table**: deduplicated by ticker symbol (positions across multiple accounts summed client-side). Investments page keeps per-account detail. Asset class badges are color-coded to match the allocation donut.
- **Alerts**: allocation drift ≥ 3%, TLH candidates (from `tax.tlh_candidates`), journal milestones.

## Transaction fields

| Field | Type | Notes |
|---|---|---|
| `txn_date` | TEXT | ISO date |
| `direction` | TEXT | `income`, `expense`, `transfer` |
| `category` | TEXT | Optional. Defaults to `uncategorized`; named values usually match a `budget_categories` name. Orphaned values are preserved in dropdowns. |
| `amount` | REAL | Always positive; sign implied by direction |
| `payee` | TEXT | Optional — counterparty name (merchant, recipient) |
| `description` | TEXT | Optional — free-text memo |
| `account_id` | INTEGER | FK to `accounts` |

## API shape notes

- `GET /api/tax` returns an **object**: `{tlh_candidates, unrealized_total, tlh_total, ytd_income_total, ytd_income_breakdown}` — not a plain array. Dashboard accesses `tlh.tlh_candidates` for alerts.
- `GET /api/accounts/{id}` returns the account row + `balance` computed live by `_compute_balances`.
- `GET /api/real-estate` returns properties with `mortgage_balance` substituted from the linked loan account when `account_id` is set, plus `linked_account_name`.
- `GET /api/budget?month=YYYY-MM` returns one month of budget planning data: categories with `planned_amount`, actuals, variance, totals, previous/next month, and uncategorized summaries.
- `PUT /api/budget/months/{month}` saves planned category amounts for that month.
- `POST /api/budget/months/{month}/copy` copies a source month into the destination month; pass `{"source_month":"YYYY-MM","overwrite":true}` to replace an existing plan.
- `GET /api/transactions` accepts optional `limit`, `category`, `direction`, `account_id`, and `month=YYYY-MM` filters. `category=uncategorized` matches blank/uncategorized rows.
- `POST /api/transactions/bulk-category` accepts `{"ids":[...],"category":"Groceries"}` for bulk assignment.
- `POST /api/reset` requires JSON body `{"confirm": "RESET"}` — returns 400 otherwise.
