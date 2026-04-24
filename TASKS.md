# FINCTL — Tasks & Roadmap

## Tier 1 — Core (complete)

- [x] Project scaffold: FastAPI + SQLite + Jinja2 + Chart.js
- [x] Dashboard: KPI tiles, NW history chart, allocation donut, cashflow, holdings, alerts, journal preview
- [x] Investments: full holdings table, allocation vs target, class performance
- [x] Accounts: grouped account list with balances; account names link to drill-down
- [x] Account drill-down: `/accounts/{id}` — transaction history, month separators, inline edit/delete
- [x] Real Estate: equity, LTV, appreciation, amortization, capex log
- [x] Tax & TLH: loss candidates, full taxable gain/loss table, YTD investment income
- [x] Budget: MTD income/expense vs target, savings rate
- [x] Journal: log with tags and milestones, inline edit/delete
- [x] Price refresh: `yfinance` integration, manual "Refresh Prices" button
- [x] Daily price auto-refresh: APScheduler background job, Mon–Fri 4:05pm ET
- [x] Market ticker strip: scrolling marquee — major indices + holdings, daily % change, `prev_close` in prices table
- [x] Snapshot workflow: per-account balance form + "Record Snapshot"
- [x] Transaction entry: add income/expense entries from /data page
- [x] Transaction-based balance architecture: `_compute_balances()` — live from transactions + holdings, not snapshots
- [x] Debt tracking: credit/loan accounts compute balance from transactions; opening_balance anchor; payoff projection on account detail
- [x] Real estate ↔ loan account link: `real_estate.account_id` → mortgage balance from linked loan; double-count prevention in `debt_total`
- [x] Transaction payee field: `payee` column on transactions table; shown in account drill-down and Data → Transactions; inline edit/delete

## Tier 2 — Data import (complete)

- [x] CSV snapshot import — inside Snapshot tab on /data; date + NW + cash + invested + equity columns; upsert on date; backfill up to 10 years of history
- [x] CSV transaction import — bank export → transactions table; inside Transactions tab on /data
- [x] CSV holdings import — Fidelity/Schwab/Vanguard format → holdings table; inside Holdings tab on /data; account selector; INSERT OR REPLACE keyed on (account_id, symbol)

## Tier 3 — Analysis depth

- [x] Realized gains / investment income YTD — Tax page: 3 KPI tiles (unrealized total, YTD income, harvestable losses) + YTD income breakdown by category + all holdings table
- [x] Net worth projection — "Proj" toggle on dashboard NW chart; dashed 10-year overlay using trailing CAGR from visible history slice; anchored to live NW value
- [x] Rebalance calculator — `/rebalance` page + `GET /api/rebalance?new_cash=N`; tax-aware priority: TLH candidates first → tax-advantaged (IRA/401k/HSA) → taxable gains; buy targets show existing symbols per class; new cash input shifts targets to reduce/eliminate sells

## Tier 4 — Mobile & responsive UI (complete)

- [x] Responsive sidebar (hamburger drawer overlay at ≤768px)
- [x] Responsive grid: KPI tiles 2-col at ≤768px, 1-col at ≤480px; all grids stack to single column
- [x] Touch-friendly tables: horizontal scroll wrappers, larger tap targets
- [x] Fixed topbar on mobile; tighter padding; tab nav scrollable strip

## UX polish

- [x] Dashboard viewport fit: all content visible without scrolling; ticker strip always in view
- [x] NW chart: multi-line (Net Worth, Invested, Cash, Home Equity) with period filters (30D/QTD/YTD/1Y/2Y/5Y/MAX)
- [x] NW chart: "Proj" toggle adds dashed 10-year projection using trailing CAGR, anchored to live NW
- [x] KPI tiles: MoM + YTD % change sub-stats on all four tiles
- [x] KPI tiles: inline SVG sparklines (last 24 snapshots, color-coded per metric)
- [x] KPI tile order: Net Worth → Invested → Home Equity → Liquid Cash → Total Debt
- [x] Dashboard holdings: consolidate duplicate tickers into one row; investments page keeps per-account breakdown
- [x] Allocation donut: tooltip shows dollar amounts + %, legend shows all classes with values
- [x] Mortgage amortization: loan config, per-month schedule, principal/interest split, equity projection
- [x] Monthly capex/maintenance memo: editable per-month cost log, running tally, annual view
- [ ] Daily gain/loss on holdings: deferred — cumulative P&L + TLH page is likely sufficient; revisit if needed

## Data management (complete)

- [x] Holdings: add/edit/delete (Holdings tab on /data, two-row inline edit)
- [x] Accounts: add/delete/edit (Accounts tab on /data); opening balance + APR + min payment for credit/loan
- [x] Allocation targets: edit target % per asset class (Allocation tab on /data)
- [x] Budget categories: add/edit/delete (Budget tab on /data)
- [x] Real estate: add/update/delete properties (Real Estate tab on /data); linked loan account selector
- [x] Real estate: mortgage config + amortization per-property
- [x] Journal entries: add/edit/delete (inline on /journal)
- [x] Transactions: add/edit/delete (/data Transactions tab, two-row inline edit)
- [x] Transactions: inline edit/delete on account drill-down page (consistent button styles)

## Multi-portfolio

- [x] `portfolios.json` at project root — tracks named portfolios (name, db path, created_at) and active pointer
- [x] `app/portfolio.py` — load/save config, list portfolios, switch active, create new
- [x] `app/db.py` — `get_conn()` reads active DB path from portfolio config instead of hardcoded `finance.db`
- [x] `main.py` — `GET /api/portfolios`, `POST /api/portfolio/switch`, `POST /api/portfolio/new`
- [x] Sidebar portfolio switcher (Alpine.js dropdown anchored at bottom) — shows active name, lists others, inline "New portfolio" form
- [x] `init_db()` + optional `seed_demo()` called on new portfolio creation; `init_db()` called on switch to apply any pending migrations

## Personalization

- [ ] User profile: name, currency symbol, display preferences — stored in `app_flags` or a `profile` table
- [ ] Dashboard greeting ("Good morning, [Name]") driven by profile

## Business Intelligence (investigation)

- [ ] Investigate integrating existing bookkeeper utility as a Business tab
  — each business unit: P&L, balance sheet, transactions, accounts
  — upload bank/accounting statements → bookkeeper parses, categorizes, inserts
  — needs `businesses` table + scoped `business_transactions`, `business_accounts`
  — confirm bookkeeper utility path before starting

## Testing

- [ ] Write data-agnostic tests for tax/TLH logic that work against any seed data (structure checks, not hardcoded dollar values)
- [ ] Consider a test fixture with a minimal known dataset so assertions can be precise without depending on `seed_demo()`

## Infrastructure

- [ ] `ruff` linting setup
- [ ] Backup script (`finance.db` → timestamped `backups/`)
- [ ] `Makefile` with `run`, `refresh`, `snapshot` targets

## Security (complete)

- [x] Add shared `esc(s)` HTML-escape helper to `base.html` (escape `&`, `<`, `>`, `"`, `'`) and apply to all user-entered text rendered via `innerHTML` — account names, property names, budget category names, journal content, transaction memos
- [x] Add server-side guard to `POST /api/reset` — require `{"confirm":"RESET"}` JSON body to prevent DNS rebinding data-wipe
- [x] Document in README: always use `./run.sh` (binds to `127.0.0.1`) — never expose without adding authentication first
- [x] SQLite hardening: `trusted_schema=OFF`, `secure_delete=ON`

## Database (complete)

- [x] Indexes: `transactions(account_id)`, `transactions(txn_date)`, `prices(symbol, recorded_at)`, `snapshots(snapshot_date)`
- [x] `UNIQUE(account_id, symbol)` on `holdings` enforced via unique index; `add_holding` upgraded to upsert; CSV import deduplication reinforced
- [x] Performance PRAGMAs: `synchronous=NORMAL`, `temp_store=MEMORY`

## Supply chain

- [ ] Add note in README about `yfinance` outbound dependency (fetches from Yahoo Finance); users in air-gapped environments should expect price refresh to fail silently
