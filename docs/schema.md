# Schema Reference

## Tables

| Table | Purpose |
|---|---|
| `accounts` | Account registry; `type` enum controls balance computation method and display. `opening_balance` anchors transaction-based balance computation. `interest_rate` + `minimum_payment` for credit/loan payoff projection. |
| `holdings` | Positions by account; `cost_basis` is per-share; `is_manual` flag marks positions whose prices are not available on Yahoo Finance. `UNIQUE(account_id, symbol)` enforced via unique index — add/import upserts on conflict. |
| `prices` | One row per symbol per refresh; `prev_close` stores prior day's close for daily change calc; queries use correlated subquery for `MAX(recorded_at)` |
| `snapshots` | Periodic net-worth snapshots (NW chart source); stores `liquid_cash`, `invested_total`, `home_equity`, `debt_total`, `other_assets` per snapshot. **History only — not used for current balances.** |
| `account_snapshots` | Per-account balances tied to a snapshot. Used for historical reference only. |
| `real_estate` | Properties with `estimated_value` and `mortgage_balance`; `account_id` optionally links to a loan account (overrides `mortgage_balance` with computed balance) |
| `mortgage_config` | One row per property: loan amount, rate, term, payment, start date, appreciation rate. Amortization computed in Python by `get_amortization()` — not stored row-by-row. |
| `property_costs` | Per-month capex/maintenance entries; `UNIQUE(property_id, cost_year, cost_month)` |
| `transactions` | Cashflow entries; `direction` is `income`/`expense`/`transfer`; `category` defaults to `uncategorized`; `payee` is the counterparty (merchant/recipient); `description` is a free-text memo |
| `budget_categories` | Budget category definitions and default monthly targets; `direction` is `income`/`expense` |
| `budget_months` | One row per planned month (`YYYY-MM`), with optional notes |
| `budget_month_items` | Planned amount per `(month, category_id)` for zero-based monthly budgeting; cascades when a month or category is deleted |
| `journal_entries` | Notes and milestones; `is_milestone=1` entries surface in dashboard alerts |
| `allocation_targets` | Target `%` per `asset_class`; drift = actual − target |
| `app_flags` | Key/value flags; `demo_seeded` prevents re-seeding after first run |

## Valid enum values

**`account.type`:** `checking`, `savings`, `brokerage`, `retirement_401k`, `retirement_ira`, `hsa`, `credit`, `loan`, `crypto`, `other`

`credit` and `loan` are liabilities — balance = `opening_balance + net spending`.

`other` accounts (vehicles, collectibles, etc.) — balance = `opening_balance + net inflows`. Included in net worth. KPI tile and NW chart line appear on the dashboard only when at least one `other` account has a non-zero balance.

**`asset_class`:** `us_equity`, `intl_equity`, `bond`, `real_estate_fund`, `commodity`, `cash_equiv`, `crypto`, `other`

**`transaction.direction`:** `income`, `expense`, `transfer`

**`budget_categories.direction`:** `income`, `expense`

## Indexes

All indexes are created idempotently via `CREATE INDEX IF NOT EXISTS` in `init_db()`:

| Index | Table | Columns | Serves |
|---|---|---|---|
| `idx_transactions_account_id` | `transactions` | `account_id` | `_compute_balances()`, account drill-down |
| `idx_transactions_txn_date` | `transactions` | `txn_date` | MTD cashflow, budget, YTD tax queries |
| `idx_transactions_category_direction_date` | `transactions` | `category, direction, txn_date` | budget actuals, transaction filters, uncategorized inbox |
| `idx_budget_month_items_month` | `budget_month_items` | `month` | monthly budget planner |
| `idx_prices_symbol_recorded` | `prices` | `symbol, recorded_at` | latest-price correlated subquery (runs in allocation, tax, rebalance, ticker) |
| `idx_snapshots_date` | `snapshots` | `snapshot_date` | NW chart, MoM/YTD lookups |
| `idx_holdings_account_symbol` | `holdings` | `account_id, symbol` | UNIQUE enforcement; upsert conflict target |

## SQLite connection settings

Set on every connection in `get_conn()`:

| PRAGMA | Value | Reason |
|---|---|---|
| `journal_mode` | `WAL` | Concurrent reads during writes; faster for this access pattern |
| `foreign_keys` | `ON` | Enforce referential integrity |
| `synchronous` | `NORMAL` | Safe with WAL; avoids full fsync on every write |
| `temp_store` | `MEMORY` | Temp tables in RAM |
| `trusted_schema` | `OFF` | Harden against malicious schema objects |
| `secure_delete` | `ON` | Overwrite freed pages so deleted financial data can't be recovered from the file |

## Tax / TLH rules

TLH candidates are filtered to `WHERE a.type = 'brokerage'` only. Retirement, HSA, and other tax-advantaged accounts are intentionally excluded — selling at a loss inside a tax-advantaged account produces no tax benefit.
