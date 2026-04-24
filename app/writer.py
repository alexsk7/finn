"""Write operations: prices, snapshots, journal, transactions."""

from datetime import date, datetime
from .db import get_conn

INDEX_SYMBOLS = ['SPY', 'QQQ', 'DIA', 'IWM', 'GLD', 'TLT', 'BTC-USD']


# ── Prices ────────────────────────────────────────────────────────────────────

def refresh_prices(db_path=None) -> dict:
    """Fetch latest quotes for all holdings symbols plus tracked market indices."""
    import yfinance as yf

    with get_conn(db_path) as conn:
        holding_symbols = [
            r[0] for r in
            conn.execute("SELECT DISTINCT symbol FROM holdings").fetchall()
        ]

    seen: set[str] = set()
    symbols: list[str] = []
    for s in holding_symbols + INDEX_SYMBOLS:
        if s not in seen:
            seen.add(s)
            symbols.append(s)

    # Yahoo Finance uses dashes for share-class dots (BRK.B → BRK-B)
    def yf_sym(s: str) -> str:
        return s.replace(".", "-")

    updated, failed = [], []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    with get_conn(db_path) as conn:
        for symbol in symbols:
            try:
                ticker = yf.Ticker(yf_sym(symbol))
                prev_close = None
                try:
                    fi = ticker.fast_info
                    price = float(fi.last_price)
                    if not price:
                        raise ValueError("zero price from fast_info")
                    pc = fi.previous_close
                    prev_close = float(pc) if pc else None
                except Exception:
                    hist = ticker.history(period="2d")
                    if hist.empty:
                        raise ValueError("no price data returned")
                    price = float(hist["Close"].iloc[-1])
                    if len(hist) >= 2:
                        prev_close = float(hist["Close"].iloc[-2])
                conn.execute(
                    "INSERT OR REPLACE INTO prices (symbol, price, prev_close, recorded_at) VALUES (?,?,?,?)",
                    (symbol, price, prev_close, now),
                )
                updated.append({"symbol": symbol, "price": price})
            except Exception as e:
                failed.append({"symbol": symbol, "error": str(e)})

    return {"updated": updated, "failed": failed}


def update_price(symbol: str, price: float) -> None:
    """Manually record a price for a symbol."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO prices (symbol, price, recorded_at) VALUES (?,?,?)",
            (symbol.upper(), price, now),
        )


# ── Snapshots ─────────────────────────────────────────────────────────────────

ASSET_TYPES    = {"checking", "savings", "brokerage", "retirement_401k",
                  "retirement_ira", "hsa", "crypto", "other"}
LIQUID_TYPES   = {"checking", "savings"}
INVESTED_TYPES = {"brokerage", "retirement_401k", "retirement_ira", "hsa", "crypto"}
DEBT_TYPES     = {"credit", "loan"}


def save_snapshot(account_balances: list[dict], snapshot_date: str | None = None,
                  notes: str | None = None) -> dict:
    """
    Record a net-worth snapshot.

    account_balances: [{"account_id": int, "balance": float}, ...]
    The mortgage loan account should be omitted — home equity is read from
    the real_estate table directly so it isn't double-counted.
    """
    snap_date = snapshot_date or date.today().isoformat()

    with get_conn() as conn:
        accounts = {
            r["id"]: r
            for r in conn.execute("SELECT id, type FROM accounts WHERE is_active=1").fetchall()
        }
        re = conn.execute(
            "SELECT SUM(estimated_value - mortgage_balance) as equity FROM real_estate"
        ).fetchone()
        home_equity = re["equity"] or 0.0

    bal_map = {int(b["account_id"]): float(b["balance"]) for b in account_balances}

    liquid, invested, debt = 0.0, 0.0, 0.0
    for acct_id, bal in bal_map.items():
        acct = accounts.get(acct_id)
        if not acct:
            continue
        t = acct["type"]
        if t in LIQUID_TYPES:
            liquid += bal
        elif t in INVESTED_TYPES:
            invested += bal
        elif t in DEBT_TYPES:
            debt += bal

    net_worth = liquid + invested + home_equity - debt

    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO snapshots
               (snapshot_date, net_worth, liquid_cash, invested_total, home_equity, debt_total, notes)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(snapshot_date) DO UPDATE SET
                 net_worth=excluded.net_worth,
                 liquid_cash=excluded.liquid_cash,
                 invested_total=excluded.invested_total,
                 home_equity=excluded.home_equity,
                 debt_total=excluded.debt_total,
                 notes=excluded.notes""",
            (snap_date, net_worth, liquid, invested, home_equity, debt, notes),
        )
        snap_id = cur.lastrowid or conn.execute(
            "SELECT id FROM snapshots WHERE snapshot_date=?", (snap_date,)
        ).fetchone()["id"]

        conn.execute("DELETE FROM account_snapshots WHERE snapshot_id=?", (snap_id,))
        conn.executemany(
            "INSERT INTO account_snapshots (snapshot_id, account_id, balance) VALUES (?,?,?)",
            [(snap_id, b["account_id"], b["balance"]) for b in account_balances
             if int(b["account_id"]) in accounts],
        )

    return {
        "snapshot_date":  snap_date,
        "net_worth":      round(net_worth, 2),
        "liquid_cash":    round(liquid, 2),
        "invested_total": round(invested, 2),
        "home_equity":    round(home_equity, 2),
        "debt_total":     round(debt, 2),
    }


# ── Journal ───────────────────────────────────────────────────────────────────

def add_journal_entry(title: str, body: str | None = None,
                      entry_date: str | None = None, tags: str | None = None,
                      is_milestone: bool = False, milestone_value: float | None = None) -> dict:
    entry_date = entry_date or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO journal_entries
               (entry_date, title, body, tags, is_milestone, milestone_value)
               VALUES (?,?,?,?,?,?)""",
            (entry_date, title, body, tags, int(is_milestone), milestone_value),
        )
        row_id = cur.lastrowid
    return {"id": row_id, "entry_date": entry_date, "title": title}


# ── Transactions ──────────────────────────────────────────────────────────────

def add_transaction(txn_date: str, amount: float, direction: str,
                    category: str, payee: str | None = None,
                    description: str | None = None,
                    account_id: int | None = None, recurring: bool = False) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO transactions
               (txn_date, account_id, amount, direction, category, payee, description, recurring)
               VALUES (?,?,?,?,?,?,?,?)""",
            (txn_date, account_id, amount, direction, category, payee, description, int(recurring)),
        )
        row_id = cur.lastrowid
    return {"id": row_id, "txn_date": txn_date, "amount": amount, "direction": direction}


# ── Holdings ─────────────────────────────────────────────────────────────────

def add_holding(account_id: int, symbol: str, asset_class: str,
                shares: float, cost_basis: float, name: str | None = None) -> dict:
    today = date.today().isoformat()
    sym = symbol.upper()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO holdings (account_id, symbol, name, asset_class, shares, cost_basis, updated_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(account_id, symbol) DO UPDATE SET
                   name=excluded.name, asset_class=excluded.asset_class,
                   shares=excluded.shares, cost_basis=excluded.cost_basis,
                   updated_at=excluded.updated_at""",
            (account_id, sym, name, asset_class, shares, cost_basis, today),
        )
        row = conn.execute(
            "SELECT * FROM holdings WHERE account_id=? AND symbol=?", (account_id, sym)
        ).fetchone()
    return dict(row)


def update_holding(holding_id: int, account_id: int, symbol: str, asset_class: str,
                   shares: float, cost_basis: float, name: str | None = None) -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            """UPDATE holdings
               SET account_id=?, symbol=?, name=?, asset_class=?, shares=?, cost_basis=?, updated_at=?
               WHERE id=?""",
            (account_id, symbol.upper(), name, asset_class, shares, cost_basis, today, holding_id),
        )
        row = conn.execute("SELECT * FROM holdings WHERE id=?", (holding_id,)).fetchone()
    return dict(row)


def delete_holding(holding_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM holdings WHERE id=?", (holding_id,))


def get_all_holdings_raw() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT h.*, a.name as account_name, a.type as account_type
            FROM holdings h JOIN accounts a ON h.account_id=a.id
            ORDER BY a.name, h.symbol
        """).fetchall()
    return [dict(r) for r in rows]


# ── Accounts ──────────────────────────────────────────────────────────────────

def add_account(name: str, institution: str, type: str,
                notes: str | None = None,
                interest_rate: float | None = None,
                minimum_payment: float | None = None,
                opening_balance: float | None = None) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO accounts (name, institution, type, notes, interest_rate, minimum_payment, opening_balance) VALUES (?,?,?,?,?,?,?)",
            (name, institution, type, notes, interest_rate, minimum_payment, opening_balance or 0),
        )
        row = conn.execute("SELECT * FROM accounts WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def update_account(account_id: int, interest_rate: float | None,
                   minimum_payment: float | None,
                   opening_balance: float | None = None) -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE accounts SET interest_rate=?, minimum_payment=?, opening_balance=? WHERE id=?",
            (interest_rate, minimum_payment, opening_balance or 0, account_id),
        )
        row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
    return dict(row)


def delete_account(account_id: int) -> dict:
    with get_conn() as conn:
        holding_count = conn.execute(
            "SELECT COUNT(*) FROM holdings WHERE account_id=?", (account_id,)
        ).fetchone()[0]
        if holding_count > 0:
            return {"ok": False, "error": f"Account has {holding_count} holding(s). Delete or move them first."}
        conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))
    return {"ok": True}


# ── CSV Snapshot Import ───────────────────────────────────────────────────────

def import_snapshot_csv(csv_text: str) -> dict:
    import csv as _csv
    import io
    from datetime import date as _date

    COL_ALIASES = {
        'date': 'date', 'snapshot_date': 'date',
        'net_worth': 'net_worth', 'networth': 'net_worth', 'nw': 'net_worth',
        'liquid_cash': 'liquid_cash', 'cash': 'liquid_cash', 'liquid': 'liquid_cash',
        'invested_total': 'invested_total', 'invested': 'invested_total',
        'home_equity': 'home_equity', 'equity': 'home_equity',
    }

    lines = [l for l in csv_text.strip().splitlines()
             if l.strip() and not l.strip().startswith('#')]
    if not lines:
        return {"inserted": 0, "updated": 0, "skipped": 0, "errors": ["Empty input"], "total": 0}

    first_cols = [c.lower().strip() for c in lines[0].split(',')]
    has_header = any(c in COL_ALIASES for c in first_cols)

    if has_header:
        reader = _csv.DictReader(io.StringIO('\n'.join(lines)))
    else:
        fieldnames = ['date', 'net_worth', 'liquid_cash', 'invested_total', 'home_equity']
        reader = _csv.DictReader(io.StringIO('\n'.join(lines)), fieldnames=fieldnames)

    inserted = updated = skipped = 0
    errors: list[str] = []

    with get_conn() as conn:
        for i, row in enumerate(reader, 1):
            try:
                norm = {COL_ALIASES.get(k.lower().strip(), k.lower().strip()): (v or '').strip()
                        for k, v in row.items() if k}

                snap_date = norm.get('date', '').strip()
                if not snap_date:
                    errors.append(f"Row {i}: missing date")
                    skipped += 1
                    continue

                _date.fromisoformat(snap_date)  # validates format

                net_worth      = float(norm.get('net_worth',      '') or 0)
                liquid_cash    = float(norm.get('liquid_cash',    '') or 0)
                invested_total = float(norm.get('invested_total', '') or 0)
                home_equity    = float(norm.get('home_equity',    '') or 0)

                existing = conn.execute(
                    "SELECT id FROM snapshots WHERE snapshot_date=?", (snap_date,)
                ).fetchone()

                conn.execute("""
                    INSERT INTO snapshots
                      (snapshot_date, net_worth, liquid_cash, invested_total, home_equity, debt_total)
                    VALUES (?,?,?,?,?,0)
                    ON CONFLICT(snapshot_date) DO UPDATE SET
                      net_worth=excluded.net_worth,
                      liquid_cash=excluded.liquid_cash,
                      invested_total=excluded.invested_total,
                      home_equity=excluded.home_equity
                """, (snap_date, net_worth, liquid_cash, invested_total, home_equity))

                if existing:
                    updated += 1
                else:
                    inserted += 1

            except (ValueError, TypeError) as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1

    return {
        "inserted": inserted,
        "updated":  updated,
        "skipped":  skipped,
        "errors":   errors[:20],
        "total":    inserted + updated + skipped,
    }


# ── CSV Transaction Import ────────────────────────────────────────────────────

def import_transaction_csv(csv_text: str, account_id: int | None = None) -> dict:
    """
    Import transactions from CSV. Accepts common bank export formats.

    Recognized column names (case-insensitive):
      date / txn_date / transaction_date / posted_date
      amount (negative = expense if no direction column)
      direction / type / dr_cr / transaction_type
      category / merchant / payee
      description / memo / note / narrative
      account_id / account (overridden by account_id param if provided)
      recurring (0/1 or true/false, default 0)
    """
    import csv as _csv
    import io
    from datetime import date as _date

    COL_ALIASES = {
        'date': 'date', 'txn_date': 'date', 'transaction_date': 'date',
        'posted_date': 'date', 'post_date': 'date', 'posting_date': 'date',
        'amount': 'amount', 'amt': 'amount', 'debit_amount': 'amount',
        'direction': 'direction', 'type': 'direction', 'dr_cr': 'direction',
        'transaction_type': 'direction', 'credit_debit': 'direction',
        'category': 'category', 'merchant': 'category', 'payee': 'category',
        'description': 'description', 'memo': 'description', 'note': 'description',
        'narrative': 'description', 'details': 'description',
        'account_id': 'account_id', 'account': 'account_id',
        'recurring': 'recurring',
    }

    DIR_MAP = {
        'debit': 'expense', 'dr': 'expense', 'withdrawal': 'expense', 'charge': 'expense',
        'credit': 'income', 'cr': 'income', 'deposit': 'income',
        'income': 'income', 'expense': 'expense', 'transfer': 'transfer',
    }

    def parse_date(s: str) -> str:
        s = s.strip()
        for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%m-%d-%Y', '%Y/%m/%d'):
            try:
                return datetime.strptime(s, fmt).date().isoformat()
            except ValueError:
                continue
        raise ValueError(f"unrecognized date format: {s!r}")

    lines = [l for l in csv_text.strip().splitlines()
             if l.strip() and not l.strip().startswith('#')]
    if not lines:
        return {"inserted": 0, "skipped": 0, "errors": ["Empty input"], "total": 0}

    first_cols = [c.lower().strip().strip('"') for c in lines[0].split(',')]
    has_header = any(c in COL_ALIASES for c in first_cols)

    if has_header:
        reader = _csv.DictReader(io.StringIO('\n'.join(lines)))
    else:
        fieldnames = ['date', 'amount', 'direction', 'category', 'description']
        reader = _csv.DictReader(io.StringIO('\n'.join(lines)), fieldnames=fieldnames)

    inserted = skipped = 0
    errors: list[str] = []

    with get_conn() as conn:
        for i, row in enumerate(reader, 1):
            try:
                norm = {
                    COL_ALIASES.get(k.lower().strip().strip('"'), k.lower().strip()):
                    (v or '').strip().strip('"')
                    for k, v in row.items() if k
                }

                txn_date_raw = norm.get('date', '').strip()
                if not txn_date_raw:
                    errors.append(f"Row {i}: missing date")
                    skipped += 1
                    continue

                txn_date = parse_date(txn_date_raw)

                amt_raw = norm.get('amount', '').replace(',', '').replace('$', '')
                if not amt_raw:
                    errors.append(f"Row {i}: missing amount")
                    skipped += 1
                    continue
                amount_raw = float(amt_raw)

                dir_raw = norm.get('direction', '').lower().strip()
                if dir_raw:
                    direction = DIR_MAP.get(dir_raw, 'expense')
                elif amount_raw < 0:
                    direction = 'expense'
                else:
                    direction = 'income'

                amount = abs(amount_raw)
                if amount == 0:
                    skipped += 1
                    continue

                category = norm.get('category', '').strip() or 'Other'
                description = norm.get('description', '').strip() or None

                row_acct = account_id
                if row_acct is None:
                    raw_acct = norm.get('account_id', '').strip()
                    if raw_acct:
                        try:
                            row_acct = int(raw_acct)
                        except ValueError:
                            row_acct = None

                recurring_raw = norm.get('recurring', '0').strip().lower()
                recurring = 1 if recurring_raw in ('1', 'true', 'yes') else 0

                conn.execute(
                    """INSERT INTO transactions
                       (txn_date, account_id, amount, direction, category, description, recurring)
                       VALUES (?,?,?,?,?,?,?)""",
                    (txn_date, row_acct, amount, direction, category, description, recurring),
                )
                inserted += 1

            except (ValueError, TypeError) as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1

    return {
        "inserted": inserted,
        "skipped":  skipped,
        "errors":   errors[:20],
        "total":    inserted + skipped,
    }


# ── CSV Holdings Import ───────────────────────────────────────────────────────

def import_holdings_csv(csv_text: str, account_id: int) -> dict:
    """
    Import holdings from a brokerage CSV export (Fidelity, Schwab, Vanguard, etc.).

    Auto-detects the header row by scanning for a line that contains 'symbol' or
    'ticker' as a column — handles broker files that include account-metadata rows
    above the actual header.

    Recognized columns (case-insensitive):
      symbol / ticker
      description / name / investment name  → holding name
      quantity / shares / qty
      average cost basis / avg_cost         → per-share cost (preferred)
      cost_basis / cost basis total         → total cost (divided by shares)
      security_type / asset_class           → maps to holdings asset_class enum
    """
    import csv as _csv
    import io

    COL_ALIASES = {
        'symbol': 'symbol', 'ticker': 'symbol', 'sym': 'symbol',
        'description': 'name', 'name': 'name', 'security_name': 'name',
        'security': 'name', 'investment name': 'name', 'fund name': 'name',
        'quantity': 'shares', 'shares': 'shares', 'qty': 'shares', 'units': 'shares',
        'average_cost_basis': 'cost_per_share', 'average cost basis': 'cost_per_share',
        'avg_cost': 'cost_per_share', 'average_cost': 'cost_per_share',
        'unit_cost': 'cost_per_share', 'cost_per_share': 'cost_per_share',
        'cost_basis_per_share': 'cost_per_share',
        'cost_basis': 'cost_total', 'cost basis': 'cost_total',
        'cost_basis_total': 'cost_total', 'cost basis total': 'cost_total',
        'total_cost': 'cost_total', 'total cost': 'cost_total',
        'asset_class': 'asset_class', 'type': 'asset_class',
        'security_type': 'asset_class', 'security type': 'asset_class',
    }

    CLASS_MAP = {
        'equity': 'us_equity', 'stock': 'us_equity', 'etf': 'us_equity',
        'mutual fund': 'us_equity', 'fund': 'us_equity',
        'exchange-traded fund': 'us_equity', 'exchange traded fund': 'us_equity',
        'bond': 'bond', 'fixed income': 'bond', 'fixed_income': 'bond',
        'cash & money market': 'cash_equiv', 'cash and money market': 'cash_equiv',
        'money market': 'cash_equiv',
        'crypto': 'crypto', 'cryptocurrency': 'crypto',
        'reit': 'real_estate_fund', 'real estate': 'real_estate_fund',
        'commodity': 'commodity',
    }

    VALID_CLASSES = {
        'us_equity', 'intl_equity', 'bond', 'real_estate_fund',
        'commodity', 'cash_equiv', 'crypto', 'other',
    }

    SKIP_SYMBOLS = {
        'account total', 'total', 'pending activity', 'pending',
        'subtotal', 'grand total',
    }

    def clean_float(s: str) -> float:
        return float(s.strip().replace('$', '').replace(',', '').replace('%', '').replace('+', '') or 0)

    lines = [l for l in csv_text.strip().splitlines() if l.strip()]
    if not lines:
        return {"inserted": 0, "updated": 0, "skipped": 0, "errors": ["Empty input"], "total": 0}

    # Find header row — first line with 'symbol' or 'ticker' as a column value
    header_idx = None
    for i, line in enumerate(lines):
        cols = [c.strip().strip('"').lower() for c in line.split(',')]
        if any(c in ('symbol', 'ticker', 'sym') for c in cols):
            header_idx = i
            break

    if header_idx is None:
        return {
            "inserted": 0, "updated": 0, "skipped": 0,
            "errors": ["Could not detect header row — CSV must contain a 'Symbol' column"],
            "total": 0,
        }

    reader = _csv.DictReader(io.StringIO('\n'.join(lines[header_idx:])))

    inserted = updated = skipped = 0
    errors: list[str] = []
    today = date.today().isoformat()

    with get_conn() as conn:
        for i, row in enumerate(reader, 1):
            try:
                norm = {
                    COL_ALIASES.get(k.strip().strip('"').lower(), k.strip().lower()):
                    (v or '').strip().strip('"')
                    for k, v in row.items() if k
                }

                symbol = norm.get('symbol', '').strip().upper()
                if not symbol or symbol.startswith('--') or symbol.lower() in SKIP_SYMBOLS:
                    skipped += 1
                    continue

                shares_raw = norm.get('shares', '').strip()
                if not shares_raw:
                    skipped += 1
                    continue
                shares = clean_float(shares_raw)
                if shares <= 0:
                    skipped += 1
                    continue

                # Prefer explicit per-share cost; fall back to total ÷ shares
                cost_raw = norm.get('cost_per_share', '').strip()
                if cost_raw:
                    cost_per_share = clean_float(cost_raw)
                else:
                    cost_total_raw = norm.get('cost_total', '').strip()
                    if cost_total_raw:
                        cost_total = clean_float(cost_total_raw)
                        cost_per_share = round(cost_total / shares, 6) if shares else 0.0
                    else:
                        cost_per_share = 0.0

                name = norm.get('name', '').strip() or None

                cls_raw = norm.get('asset_class', '').strip().lower()
                if cls_raw in VALID_CLASSES:
                    asset_class = cls_raw
                else:
                    asset_class = CLASS_MAP.get(cls_raw, 'us_equity')

                existing = conn.execute(
                    "SELECT id FROM holdings WHERE account_id=? AND symbol=?",
                    (account_id, symbol),
                ).fetchone()

                if existing:
                    conn.execute(
                        """UPDATE holdings
                           SET name=?, asset_class=?, shares=?, cost_basis=?, updated_at=?
                           WHERE id=?""",
                        (name, asset_class, shares, cost_per_share, today, existing['id']),
                    )
                    updated += 1
                else:
                    conn.execute(
                        """INSERT INTO holdings
                           (account_id, symbol, name, asset_class, shares, cost_basis, updated_at)
                           VALUES (?,?,?,?,?,?,?)""",
                        (account_id, symbol, name, asset_class, shares, cost_per_share, today),
                    )
                    inserted += 1

            except (ValueError, TypeError) as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1
            except Exception as e:
                errors.append(f"Row {i}: {e}")
                skipped += 1

    return {
        "inserted": inserted,
        "updated":  updated,
        "skipped":  skipped,
        "errors":   errors[:20],
        "total":    inserted + updated + skipped,
    }


# ── Reset ─────────────────────────────────────────────────────────────────────

def reset_all_data() -> None:
    """Wipe all user data and mark as never-seeded so seed_demo won't re-fire."""
    with get_conn() as conn:
        conn.executescript("""
            DELETE FROM account_snapshots;
            DELETE FROM snapshots;
            DELETE FROM holdings;
            DELETE FROM prices;
            DELETE FROM transactions;
            DELETE FROM journal_entries;
            DELETE FROM budget_categories;
            DELETE FROM allocation_targets;
            DELETE FROM real_estate;
            DELETE FROM accounts;
            DELETE FROM app_flags;
        """)


# ── Mortgage / Amortization ───────────────────────────────────────────────────

def save_mortgage_config(property_id: int, loan_amount: float, annual_rate_pct: float,
                         term_months: int, monthly_payment: float, start_date: str,
                         appreciation_rate: float = 2.5) -> dict:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO mortgage_config
              (property_id, loan_amount, annual_rate_pct, term_months,
               monthly_payment, start_date, appreciation_rate)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(property_id) DO UPDATE SET
              loan_amount=excluded.loan_amount,
              annual_rate_pct=excluded.annual_rate_pct,
              term_months=excluded.term_months,
              monthly_payment=excluded.monthly_payment,
              start_date=excluded.start_date,
              appreciation_rate=excluded.appreciation_rate
        """, (property_id, loan_amount, annual_rate_pct, term_months,
              monthly_payment, start_date, appreciation_rate))
        row = conn.execute(
            "SELECT * FROM mortgage_config WHERE property_id=?", (property_id,)
        ).fetchone()
    return dict(row)


def upsert_property_cost(property_id: int, cost_year: int, cost_month: int,
                         amount: float, memo: str | None) -> dict:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO property_costs (property_id, cost_year, cost_month, amount, memo)
            VALUES (?,?,?,?,?)
            ON CONFLICT(property_id, cost_year, cost_month) DO UPDATE SET
              amount=excluded.amount, memo=excluded.memo
        """, (property_id, cost_year, cost_month, amount, memo))
        row = conn.execute("""
            SELECT * FROM property_costs
            WHERE property_id=? AND cost_year=? AND cost_month=?
        """, (property_id, cost_year, cost_month)).fetchone()
    return dict(row)


# ── Allocation Targets ────────────────────────────────────────────────────────

def upsert_allocation_target(asset_class: str, target_pct: float) -> dict:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO allocation_targets (asset_class, target_pct)
            VALUES (?,?)
            ON CONFLICT(asset_class) DO UPDATE SET target_pct=excluded.target_pct
        """, (asset_class, target_pct))
        row = conn.execute(
            "SELECT * FROM allocation_targets WHERE asset_class=?", (asset_class,)
        ).fetchone()
    return dict(row)


# ── Budget Categories ─────────────────────────────────────────────────────────

def add_budget_category(name: str, monthly_target: float, direction: str) -> dict:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO budget_categories (name, monthly_target, direction) VALUES (?,?,?)",
            (name, monthly_target, direction),
        )
        row = conn.execute(
            "SELECT * FROM budget_categories WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def update_budget_category(category_id: int, name: str, monthly_target: float) -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE budget_categories SET name=?, monthly_target=? WHERE id=?",
            (name, monthly_target, category_id),
        )
        row = conn.execute(
            "SELECT * FROM budget_categories WHERE id=?", (category_id,)
        ).fetchone()
    return dict(row)


def delete_budget_category(category_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM budget_categories WHERE id=?", (category_id,))


# ── Journal ── edit / delete ──────────────────────────────────────────────────

def update_journal_entry(entry_id: int, title: str, body: str | None = None,
                         entry_date: str | None = None, tags: str | None = None,
                         is_milestone: bool = False,
                         milestone_value: float | None = None) -> dict:
    with get_conn() as conn:
        conn.execute("""
            UPDATE journal_entries
            SET title=?, body=?, entry_date=?, tags=?, is_milestone=?, milestone_value=?
            WHERE id=?
        """, (title, body, entry_date, tags, int(is_milestone), milestone_value, entry_id))
        row = conn.execute(
            "SELECT * FROM journal_entries WHERE id=?", (entry_id,)
        ).fetchone()
    return dict(row) if row else {}


def delete_journal_entry(entry_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM journal_entries WHERE id=?", (entry_id,))


# ── Transactions ── delete ────────────────────────────────────────────────────

def update_transaction(txn_id: int, txn_date: str, amount: float, direction: str,
                       category: str, payee: str | None = None,
                       description: str | None = None,
                       account_id: int | None = None) -> dict:
    with get_conn() as conn:
        conn.execute(
            """UPDATE transactions
               SET txn_date=?, account_id=?, amount=?, direction=?, category=?,
                   payee=?, description=?
               WHERE id=?""",
            (txn_date, account_id, amount, direction, category, payee, description, txn_id),
        )
        row = conn.execute("SELECT * FROM transactions WHERE id=?", (txn_id,)).fetchone()
    return dict(row)


def delete_transaction(txn_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))


# ── Real Estate ───────────────────────────────────────────────────────────────

def add_real_estate(name: str, estimated_value: float, mortgage_balance: float,
                    address: str | None = None, purchase_price: float = 0,
                    purchase_date: str | None = None,
                    account_id: int | None = None) -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO real_estate
               (name, address, estimated_value, mortgage_balance, purchase_price, purchase_date, updated_at, account_id)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, address, estimated_value, mortgage_balance, purchase_price, purchase_date, today, account_id),
        )
        row = conn.execute("SELECT * FROM real_estate WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def link_real_estate_account(property_id: int, account_id: int | None) -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE real_estate SET account_id=? WHERE id=?",
            (account_id, property_id),
        )
        row = conn.execute("SELECT * FROM real_estate WHERE id=?", (property_id,)).fetchone()
    return dict(row)


def delete_real_estate(property_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT name FROM real_estate WHERE id=?", (property_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "Property not found"}
        conn.execute("DELETE FROM real_estate WHERE id=?", (property_id,))
    return {"ok": True}


def update_real_estate(property_id: int, estimated_value: float,
                       mortgage_balance: float) -> dict:
    today = date.today().isoformat()
    with get_conn() as conn:
        conn.execute(
            """UPDATE real_estate
               SET estimated_value=?, mortgage_balance=?, updated_at=?
               WHERE id=?""",
            (estimated_value, mortgage_balance, today, property_id),
        )
        row = conn.execute("SELECT * FROM real_estate WHERE id=?", (property_id,)).fetchone()
    return dict(row)
