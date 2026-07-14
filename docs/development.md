# Development Guide

## Adding a new page

1. Add a query function to `app/queries.py`
2. Add a GET route to `main.py` using the `page()` helper with a new `active` key
3. Add the nav link to `templates/base.html` sidebar with the matching `active` check
4. Create `templates/<name>.html` extending `base.html`; fetch data in `{% block scripts %}`
5. For multi-column layouts that need to collapse on mobile, use a named layout class from `style.css`

## Adding a new API endpoint

1. Add a read function to `app/queries.py` or write function to `app/writer.py`
2. Add a Pydantic model (for POST/PUT bodies) and route to `main.py`
3. Import the function in `main.py` (in the relevant `from app.queries import ...` or `from app.writer import ...` block)
4. Call from JS via `fetch('/api/...')` in the relevant template

## Adding a CSV import to a tab

Follow the snapshot tab pattern: add a second card below the main form in the relevant tab panel.

- **Backend**: add a parser function in `writer.py` using `csv.DictReader`. Detect the header by checking first-row column names, normalize aliases, upsert.
- **Frontend**: file picker + textarea + live preview (first 6 rows) + Import button + result summary.
- Do not create a standalone "Import CSV" tab — imports always live inside their corresponding tab.
- Transaction imports should keep `payee` / `merchant` separate from `category`. Missing transaction categories should become `uncategorized`, then be handled through the Transactions inbox.

## Budget changes

Zero-based budget planning spans three layers:

- `budget_categories` defines category names, direction, and default target.
- `budget_months` creates a specific `YYYY-MM` planning period.
- `budget_month_items` stores planned amounts per category for that month.

When changing budget behavior, update `get_budget_month()` in `queries.py`, the month write helpers in `writer.py`, and the `/api/budget*` routes in `main.py`. Keep `/api/cashflow` working until callers have fully moved to `/api/budget`.

## Schema migrations

Add idempotent `ALTER TABLE` statements inside the try/except block after `executescript` in `db.py`. Each migration should be safe to run on a database that already has the column.

Indexes are created with `CREATE INDEX IF NOT EXISTS` — add them after the try/except migration block, not inside try/except (they are safe to re-run). Example:

```python
conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_transactions_account_id
    ON transactions(account_id)
""")
```

For a new `UNIQUE` constraint on an existing table, deduplicate first, then create a unique index:

```python
try:
    conn.execute("DELETE FROM t WHERE id NOT IN (SELECT MAX(id) FROM t GROUP BY col_a, col_b)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_t_cols ON t(col_a, col_b)")
except Exception:
    pass
```

## Adding or moving an account type

Account types are bucketed into four sets that control how balances flow into net worth. Both files must stay in sync:

| File | Sets |
|---|---|
| `app/queries.py` | `_INVESTMENT_TYPES`, `_CASH_TYPES`, `_OTHER_TYPES`, `_DEBT_TYPES` |
| `app/writer.py` | `INVESTED_TYPES`, `LIQUID_TYPES`, `OTHER_TYPES`, `DEBT_TYPES` |

The `snapshots` table stores per-bucket totals (`invested_total`, `liquid_cash`, `other_assets`, `debt_total`). Adding a new bucket requires a schema migration and a new column. Dashboard KPI tiles and the NW chart dataset list in `dashboard.html` must also be updated to surface the new bucket.

## XSS safety

All user-entered strings rendered via `innerHTML` must be passed through `esc(s)`, the global HTML-escape helper defined in `base.html`. It escapes `&`, `<`, `>`, `"`, and `'`. Apply it to any string field from the API that appears in a template literal assigned to `innerHTML`.

## Running one-off Python

```bash
mise exec -- uv run python -c "from app.db import get_conn; ..."
```

## Linting

```bash
make lint
```

For an ad hoc run without Make:

```bash
mise exec -- ruff check .
```

## Type checking

```bash
make typecheck
```

For an ad hoc run without Make:

```bash
mise exec -- ty check .
```

## Combined checks

```bash
make check
```

This runs both Ruff and ty using the existing project configuration.

## Git hooks

```bash
make hooks
```

The repo stores its Git hooks in `.githooks/`.
`make setup` installs them automatically by setting `core.hooksPath`.
The pre-commit hook runs `make check`.
The pre-push hook runs `make coverage`, optionally opens the coverage dashboard, and blocks
push only when added executable Python lines are below 80% coverage.

## Tests

```bash
make test
```

For targeted runs:

```bash
mise exec -- uv run pytest tests/test_writer_prices.py
mise exec -- uv run pytest tests/test_api_smoke.py
```

Testing conventions:

- Reuse fixtures from `tests/conftest.py`.
- Default to the per-test DB lifecycle fixture (`test_db_lifecycle`) for explicit setup/teardown and DB artifact cleanup.
- Use `minimal_seed_data` for deterministic assertions instead of full `seed_demo()` data.
- Mock Yahoo Finance calls via `mock_yfinance_ticker`; tests must not depend on network access.
- Freeze time-sensitive behavior with `frozen_now` when asserting timestamps or date-driven logic.
- Prefer data-agnostic assertions for tax/TLH logic (structure and behavior checks, not hardcoded dollar values).

### CI coverage artifact example (GitHub Actions)

`make test` generates `coverage.json`.

GitHub-hosted runners do not provide native Rocky Linux or Alpine labels.
Use a pinned Ubuntu host runner with a Linux container, or use self-hosted runners.

Example: Rocky Linux container on a pinned host runner:

```yaml
name: ci

on:
    pull_request:
    push:
        branches: [main]

jobs:
    test:
        runs-on: ubuntu-24.04
        container:
            image: rockylinux:9

        steps:
            - uses: actions/checkout@v4

            - name: Install container deps
                run: dnf -y install bash curl git tar gzip unzip xz

            - name: Install mise
                run: curl https://mise.run | sh

            - name: Add mise to PATH
                run: echo "$HOME/.local/bin" >> $GITHUB_PATH

            - name: Sync dependencies
                run: mise exec -- uv sync

            - name: Run tests with coverage
                run: make test

            - name: Upload coverage.json
                uses: actions/upload-artifact@v4
                with:
                    name: coverage-json
                    path: coverage.json
```

            If you want true native execution on Rocky Linux or Alpine, use a self-hosted runner (for example `runs-on: [self-hosted, linux, rockylinux]`).
