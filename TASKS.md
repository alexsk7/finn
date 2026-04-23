# FINCTL — Tasks & Roadmap

## Tier 1 — Core (complete)

- [x] Project scaffold: FastAPI + SQLite + Jinja2 + Chart.js
- [x] Dashboard: KPI tiles, NW history chart, allocation donut, cashflow, holdings, alerts, journal preview
- [x] Investments: full holdings table, allocation vs target, class performance
- [x] Accounts: grouped account list with balances; account names link to drill-down
- [x] Account drill-down: `/accounts/{id}` — transaction history, month separators, inline edit/delete
- [x] Real Estate: equity, LTV, appreciation
- [x] Tax & TLH: loss candidates, full taxable gain/loss table
- [x] Budget: MTD income/expense vs target, savings rate
- [x] Journal: log with tags and milestones, inline edit/delete
- [x] Price refresh: `yfinance` integration, manual "Refresh Prices" button
- [x] Daily price auto-refresh: APScheduler background job, Mon–Fri 4:05pm ET
- [x] Market ticker strip: scrolling marquee — major indices + holdings, daily % change, `prev_close` in prices table
- [x] Snapshot workflow: per-account balance form + "Record Snapshot"
- [x] Transaction entry: add income/expense entries from /data page

## Tier 2 — Data import

- [x] CSV snapshot import — inside Snapshot tab on /data; date + NW + cash + invested + equity columns; upsert on date; backfill up to 10 years of history
- [x] CSV transaction import — bank export → transactions table; inside Transactions tab on /data
- [ ] CSV holdings import — Fidelity/Schwab/Vanguard format → holdings table; inside Holdings tab on /data

## Tier 3 — Analysis depth

- [ ] Realized gains this year — tax page addition; sum of (sell price − cost basis) for closed positions
- [ ] Rebalance calculator — exact buy/sell amounts to hit targets, tax-aware:
  — prioritize selling losers (TLH candidates) in taxable accounts first
  — prefer rebalancing via buys in taxable + sells in tax-advantaged (IRA/401k) to minimize tax drag
  — surface TLH opportunities alongside rebalance trades, not as a separate step
- [ ] Net worth projection — extrapolate from trailing CAGR; 5/10/20yr overlay chart
- [ ] Debt tracking — credit cards + loans UI surface:
  — `accounts` schema already supports `credit` and `loan` types
  — dashboard debt KPI card or section (net worth already deducts debt via `debt_total` in snapshots)
  — per-account payoff timeline / interest projection
  — data entry: balance + interest rate + minimum payment per account

## Tier 4 — Mobile & responsive UI (complete)

- [x] Responsive sidebar (hamburger drawer overlay at ≤768px)
- [x] Responsive grid: KPI tiles 2-col at ≤768px, 1-col at ≤480px; all grids stack to single column
- [x] Touch-friendly tables: horizontal scroll wrappers, larger tap targets
- [x] Fixed topbar on mobile; tighter padding; tab nav scrollable strip

## UX polish

- [x] Dashboard viewport fit: all content visible without scrolling; ticker strip always in view
- [x] NW chart: multi-line (Net Worth, Invested, Cash, Home Equity) with period filters (30D/QTD/YTD/1Y/2Y/5Y/MAX)
- [x] KPI tiles: MoM + YTD % change sub-stats on all four tiles
- [x] KPI tiles: inline SVG sparklines (last 24 snapshots, color-coded per metric)
- [x] KPI tile order: Net Worth → Invested → Home Equity → Liquid Cash
- [x] Dashboard holdings: consolidate duplicate tickers into one row; investments page keeps per-account breakdown
- [x] Allocation donut: tooltip shows dollar amounts + %, legend shows all classes with values
- [x] Mortgage amortization: loan config, per-month schedule, principal/interest split, equity projection
- [x] Monthly capex/maintenance memo: editable per-month cost log, running tally, annual view
- [ ] Daily gain/loss on holdings: deferred — cumulative P&L + TLH page is likely sufficient; revisit if needed

## Data management (complete)

- [x] Holdings: add/edit/delete (Holdings tab on /data, two-row inline edit)
- [x] Accounts: add/delete (Accounts tab on /data)
- [x] Allocation targets: edit target % per asset class (Allocation tab on /data)
- [x] Budget categories: add/edit/delete (Budget tab on /data)
- [x] Real estate: add/update/delete properties (Real Estate tab on /data)
- [x] Real estate: mortgage config + amortization per-property
- [x] Journal entries: add/edit/delete (inline on /journal)
- [x] Transactions: add/edit/delete (/data Transactions tab, two-row inline edit)
- [x] Transactions: inline edit/delete on account drill-down page (consistent button styles)

## Personalization

- [ ] User profile: name, currency symbol, display preferences — stored in `app_flags` or a `profile` table
- [ ] Dashboard greeting ("Good morning, [Name]") driven by profile

## Business Intelligence (investigation)

- [ ] Investigate integrating existing bookkeeper utility as a Business tab
  — each business unit: P&L, balance sheet, transactions, accounts
  — upload bank/accounting statements → bookkeeper parses, categorizes, inserts
  — needs `businesses` table + scoped `business_transactions`, `business_accounts`
  — confirm bookkeeper utility path before starting

## Infrastructure

- [ ] `ruff` linting setup
- [ ] Backup script (`finance.db` → timestamped `backups/`)
- [ ] `Makefile` with `run`, `refresh`, `snapshot` targets
