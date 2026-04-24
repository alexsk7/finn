# Schema Reference

## Tables

| Table | Purpose |
|---|---|
| `accounts` | Account registry; `type` enum controls balance computation method and display. `opening_balance` anchors transaction-based balance computation. `interest_rate` + `minimum_payment` for credit/loan payoff projection. |
| `holdings` | Positions by account; `cost_basis` is per-share |
| `prices` | One row per symbol per refresh; `prev_close` stores prior day's close for daily change calc; queries use correlated subquery for `MAX(recorded_at)` |
| `snapshots` | Periodic net-worth snapshots (NW chart source); stores `liquid_cash`, `invested_total`, `home_equity`, `debt_total` per snapshot. **History only — not used for current balances.** |
| `account_snapshots` | Per-account balances tied to a snapshot. Used for historical reference only. |
| `real_estate` | Properties with `estimated_value` and `mortgage_balance`; `account_id` optionally links to a loan account (overrides `mortgage_balance` with computed balance) |
| `mortgage_config` | One row per property: loan amount, rate, term, payment, start date, appreciation rate. Amortization computed in Python by `get_amortization()` — not stored row-by-row. |
| `property_costs` | Per-month capex/maintenance entries; `UNIQUE(property_id, cost_year, cost_month)` |
| `transactions` | Cashflow entries; `direction` is `income`/`expense`/`transfer` |
| `budget_categories` | Monthly targets joined against transactions for actuals; `direction` is `income`/`expense` |
| `journal_entries` | Notes and milestones; `is_milestone=1` entries surface in dashboard alerts |
| `allocation_targets` | Target `%` per `asset_class`; drift = actual − target |
| `app_flags` | Key/value flags; `demo_seeded` prevents re-seeding after first run |

## Valid enum values

**`account.type`:** `checking`, `savings`, `brokerage`, `retirement_401k`, `retirement_ira`, `hsa`, `credit`, `loan`, `crypto`, `other`

`credit` and `loan` are liabilities — balance = `opening_balance + net spending`.

**`asset_class`:** `us_equity`, `intl_equity`, `bond`, `real_estate_fund`, `commodity`, `cash_equiv`, `crypto`, `other`

**`transaction.direction`:** `income`, `expense`, `transfer`

**`budget_categories.direction`:** `income`, `expense`

## Tax / TLH rules

TLH candidates are filtered to `WHERE a.type = 'brokerage'` only. Retirement, HSA, and other tax-advantaged accounts are intentionally excluded — selling at a loss inside a tax-advantaged account produces no tax benefit.
