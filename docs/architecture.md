# Architecture

## Overview

Local-first, single-process web app. No authentication, no external API dependencies, no build step.

## Request flow

1. Browser hits a page route (`/`, `/investments`, etc.) in `main.py`
2. FastAPI renders a Jinja2 template via the shared `page()` helper — only `active` (sidebar key) is passed as context. Exception: `/accounts/{account_id}` also passes `account_id`.
3. The HTML shell makes `fetch()` calls to `/api/*` endpoints on load
4. API endpoints call `app/queries.py` (reads) or `app/writer.py` (writes) and return JSON
5. JS in `{% block scripts %}` builds the UI from the response

## Data layer (`app/`)

- **`db.py`** — `get_conn()` opens SQLite with WAL mode and `row_factory=sqlite3.Row`. `init_db()` creates all tables idempotently and applies migrations. DB file lives at project root as `finance.db`. Idempotent column migrations are applied after `executescript` in a try/except block; indexes are created via `CREATE INDEX IF NOT EXISTS`.
- **`queries.py`** — all read queries. No ORM; plain SQL. Key functions: `_compute_balances(conn)`, `get_dashboard_summary`, `get_allocation`, `get_tax_summary`, `get_ticker_data`, `get_account_by_id` / `get_account_transactions`, `get_accounts_summary`, `get_real_estate`, `get_amortization`, `get_cashflow_by_category`, `get_journal`, `get_transactions`, `get_allocation_targets`, `get_budget_categories_full`.
- **`writer.py`** — all write operations: prices (`refresh_prices`, `update_price`), snapshots (`save_snapshot`, `import_snapshot_csv`), holdings CRUD + `import_holdings_csv`, account CRUD (`add_account`, `update_account`, `delete_account`), real estate (add/update/delete + `link_real_estate_account` + mortgage config + property costs), allocation targets (upsert), budget categories (add/edit/delete), journal (add/edit/delete), transactions (`add_transaction`, `update_transaction`, `delete_transaction`, `import_transaction_csv`), `reset_all_data`.
- **`seed.py`** — inserts demo data once, guarded via `app_flags` table (`demo_seeded` key).

## Background jobs

APScheduler `BackgroundScheduler` starts at module load in `main.py`. One cron job: Mon–Fri 16:05 America/New_York, calls `refresh_prices()`. Skips silently if no holdings exist. Cleaned up via `atexit`. Dependency: `apscheduler>=3.10,<4`.

## SQLite connection settings

`get_conn()` applies the following PRAGMAs on every connection:

| PRAGMA | Value | Reason |
|---|---|---|
| `journal_mode` | `WAL` | Concurrent reads; faster for single-writer workload |
| `foreign_keys` | `ON` | Enforce referential integrity |
| `synchronous` | `NORMAL` | Safe with WAL; skips full fsync — faster writes |
| `temp_store` | `MEMORY` | Temp tables in RAM |
| `trusted_schema` | `OFF` | Harden against malicious schema objects |
| `secure_delete` | `ON` | Overwrite freed pages so deleted financial data is unrecoverable |

## Balance architecture

**Current account balances are computed live from transactions and holdings — NOT from snapshots.**

`_compute_balances(conn)` returns `{account_id: float}` for all active accounts:

| Account type | Source |
|---|---|
| `brokerage`, `retirement_*`, `hsa`, `crypto` | `SUM(shares × latest_price)` from holdings |
| `checking`, `savings`, `other` | `opening_balance + SUM(income) - SUM(expense)` from transactions |
| `credit`, `loan` | `opening_balance + SUM(expense) - SUM(income)` from transactions |

`opening_balance` (column on `accounts`, default 0) anchors transaction-based computation — set it to the known balance on the day you started tracking. Investment accounts ignore `opening_balance`.

**Snapshots are history-only.** They feed the NW chart and MoM/YTD % change comparisons but are not the source of truth for current balances.

**Dashboard KPI values** (`net_worth`, `liquid_cash`, `invested`, `debt_total`, `home_equity`) are all computed live from `_compute_balances()` + real estate data.

**Double-count prevention:** Loan accounts linked to a real estate property via `real_estate.account_id` are excluded from `debt_total` — their balance is already captured as a reduction in `home_equity`. The set of `linked_mortgage_ids` is computed at query time.

## Real estate ↔ loan account link

`real_estate.account_id` (nullable FK) optionally links a property to a loan account. When set:
- Property's `mortgage_balance` = linked loan account's computed balance (live, from transactions)
- `home_equity` on the dashboard updates automatically as loan payments are logged
- The linked loan account is excluded from `debt_total` (to avoid double-counting)

Set/clear via `POST /api/real-estate/{id}/link-account` with `{"account_id": int | null}`. UI: "Linked Loan Account" dropdown on each property in Data → Real Estate tab.

## Security

- All SQL uses parameterized `?` placeholders — no string interpolation.
- `POST /api/reset` requires `{"confirm": "RESET"}` in the request body; returns HTTP 400 otherwise.
- All user-entered strings rendered via `innerHTML` are HTML-escaped via the global `esc(s)` helper defined in `base.html`.
- The server binds to `127.0.0.1` (loopback only). Do not expose on a network interface without adding an authenticating reverse proxy.
