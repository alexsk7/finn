"""SQLite database — schema init and connection helper."""

import sqlite3


def get_conn(db_path=None) -> sqlite3.Connection:
    if db_path is None:
        from .portfolio import get_active_path

        db_path = get_active_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")  # safe with WAL; faster writes
    conn.execute("PRAGMA temp_store=MEMORY")  # temp tables in RAM
    conn.execute("PRAGMA trusted_schema=OFF")  # harden against malicious schema objects
    conn.execute("PRAGMA secure_delete=ON")  # overwrite freed pages on delete
    return conn


def init_db(db_path=None) -> None:
    with get_conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id          INTEGER PRIMARY KEY,
                name        TEXT NOT NULL,
                institution TEXT NOT NULL,
                type        TEXT NOT NULL CHECK(type IN (
                                'checking','savings','brokerage',
                                'retirement_401k','retirement_ira',
                                'credit','loan','hsa','crypto','other')),
                currency    TEXT NOT NULL DEFAULT 'USD',
                is_active   INTEGER NOT NULL DEFAULT 1,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS holdings (
                id          INTEGER PRIMARY KEY,
                account_id  INTEGER NOT NULL REFERENCES accounts(id),
                symbol      TEXT NOT NULL,
                name        TEXT,
                asset_class TEXT NOT NULL CHECK(asset_class IN (
                                'us_equity','intl_equity','bond',
                                'real_estate_fund','commodity',
                                'cash_equiv','crypto','other')),
                shares      REAL NOT NULL DEFAULT 0,
                cost_basis  REAL NOT NULL DEFAULT 0,
                updated_at  TEXT NOT NULL DEFAULT (date('now'))
            );

            CREATE TABLE IF NOT EXISTS prices (
                id          INTEGER PRIMARY KEY,
                symbol      TEXT NOT NULL,
                price       REAL NOT NULL,
                prev_close  REAL,
                recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(symbol, recorded_at)
            );

            CREATE TABLE IF NOT EXISTS snapshots (
                id              INTEGER PRIMARY KEY,
                snapshot_date   TEXT NOT NULL UNIQUE,
                net_worth       REAL NOT NULL,
                liquid_cash     REAL NOT NULL DEFAULT 0,
                invested_total  REAL NOT NULL DEFAULT 0,
                home_equity     REAL NOT NULL DEFAULT 0,
                debt_total      REAL NOT NULL DEFAULT 0,
                other_assets    REAL NOT NULL DEFAULT 0,
                notes           TEXT
            );

            CREATE TABLE IF NOT EXISTS account_snapshots (
                id          INTEGER PRIMARY KEY,
                snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
                account_id  INTEGER NOT NULL REFERENCES accounts(id),
                balance     REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS real_estate (
                id                  INTEGER PRIMARY KEY,
                name                TEXT NOT NULL,
                address             TEXT,
                estimated_value     REAL NOT NULL DEFAULT 0,
                mortgage_balance    REAL NOT NULL DEFAULT 0,
                purchase_price      REAL NOT NULL DEFAULT 0,
                purchase_date       TEXT,
                updated_at          TEXT NOT NULL DEFAULT (date('now'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY,
                txn_date    TEXT NOT NULL,
                account_id  INTEGER REFERENCES accounts(id),
                amount      REAL NOT NULL,
                direction   TEXT NOT NULL CHECK(direction IN ('income','expense','transfer')),
                category    TEXT NOT NULL DEFAULT 'uncategorized',
                payee       TEXT,
                description TEXT,
                recurring   INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS budget_categories (
                id              INTEGER PRIMARY KEY,
                name            TEXT NOT NULL,
                parent          TEXT,
                monthly_target  REAL NOT NULL DEFAULT 0,
                direction       TEXT NOT NULL CHECK(direction IN ('income','expense'))
            );

            CREATE TABLE IF NOT EXISTS budget_months (
                month       TEXT PRIMARY KEY,
                notes       TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS budget_month_items (
                id              INTEGER PRIMARY KEY,
                month           TEXT NOT NULL REFERENCES budget_months(month) ON DELETE CASCADE,
                category_id     INTEGER NOT NULL REFERENCES budget_categories(id) ON DELETE CASCADE,
                planned_amount  REAL NOT NULL DEFAULT 0,
                UNIQUE(month, category_id)
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id          INTEGER PRIMARY KEY,
                entry_date  TEXT NOT NULL DEFAULT (date('now')),
                title       TEXT NOT NULL,
                body        TEXT,
                tags        TEXT,
                is_milestone INTEGER NOT NULL DEFAULT 0,
                milestone_value REAL
            );

            CREATE TABLE IF NOT EXISTS allocation_targets (
                id          INTEGER PRIMARY KEY,
                asset_class TEXT NOT NULL UNIQUE,
                target_pct  REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS mortgage_config (
                id                  INTEGER PRIMARY KEY,
                property_id         INTEGER NOT NULL REFERENCES real_estate(id) ON DELETE CASCADE,
                loan_amount         REAL NOT NULL,
                annual_rate_pct     REAL NOT NULL,
                term_months         INTEGER NOT NULL,
                monthly_payment     REAL NOT NULL,
                start_date          TEXT NOT NULL,
                appreciation_rate   REAL NOT NULL DEFAULT 2.5,
                UNIQUE(property_id)
            );

            CREATE TABLE IF NOT EXISTS property_costs (
                id          INTEGER PRIMARY KEY,
                property_id INTEGER NOT NULL REFERENCES real_estate(id) ON DELETE CASCADE,
                cost_year   INTEGER NOT NULL,
                cost_month  INTEGER NOT NULL CHECK(cost_month BETWEEN 1 AND 12),
                amount      REAL NOT NULL DEFAULT 0,
                memo        TEXT,
                UNIQUE(property_id, cost_year, cost_month)
            );

            CREATE TABLE IF NOT EXISTS app_flags (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        # Idempotent migrations for existing DBs
        try:
            conn.execute("ALTER TABLE prices ADD COLUMN prev_close REAL")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN interest_rate REAL")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN minimum_payment REAL")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN opening_balance REAL DEFAULT 0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE real_estate ADD COLUMN account_id INTEGER REFERENCES accounts(id)")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE transactions ADD COLUMN payee TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE snapshots ADD COLUMN other_assets REAL NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE holdings ADD COLUMN is_manual INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        # Indexes — idempotent via IF NOT EXISTS
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_account_id
            ON transactions(account_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_txn_date
            ON transactions(txn_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_category_direction_date
            ON transactions(category, direction, txn_date)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_budget_month_items_month
            ON budget_month_items(month)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_symbol_recorded
            ON prices(symbol, recorded_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_date
            ON snapshots(snapshot_date)
        """)

        # Unique constraint on holdings(account_id, symbol) — deduplicate first,
        # then enforce via a unique index.
        try:
            conn.execute("""
                DELETE FROM holdings WHERE id NOT IN (
                    SELECT MAX(id) FROM holdings GROUP BY account_id, symbol
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_holdings_account_symbol
                ON holdings(account_id, symbol)
            """)
        except Exception:
            pass

        # Backfill the current month's planning rows from the legacy category
        # target field. New categories keep this in sync from writer.py.
        conn.execute("INSERT OR IGNORE INTO budget_months(month) VALUES (strftime('%Y-%m','now'))")
        conn.execute("""
            INSERT OR IGNORE INTO budget_month_items(month, category_id, planned_amount)
            SELECT strftime('%Y-%m','now'), id, monthly_target
            FROM budget_categories
        """)
