"""All read queries used by the API routes."""

from .db import get_conn


def get_dashboard_summary() -> dict:
    with get_conn() as conn:
        latest = conn.execute("""
            SELECT * FROM snapshots ORDER BY snapshot_date DESC LIMIT 1
        """).fetchone()

        prev = conn.execute("""
            SELECT net_worth, liquid_cash, invested_total, home_equity
            FROM snapshots ORDER BY snapshot_date DESC LIMIT 1 OFFSET 1
        """).fetchone()

        ytd_start = conn.execute("""
            SELECT net_worth, liquid_cash, invested_total, home_equity FROM snapshots
            WHERE snapshot_date <= date('now','start of year')
            ORDER BY snapshot_date DESC LIMIT 1
        """).fetchone()

        history = conn.execute("""
            SELECT snapshot_date, net_worth, liquid_cash, invested_total, home_equity
            FROM snapshots ORDER BY snapshot_date ASC
        """).fetchall()

        re = conn.execute("""
            SELECT SUM(estimated_value - mortgage_balance) as equity,
                   SUM(estimated_value) as value,
                   SUM(mortgage_balance) as debt
            FROM real_estate
        """).fetchone()

        cashflow = conn.execute("""
            SELECT
                SUM(CASE WHEN direction='income'  THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN direction='expense' THEN amount ELSE 0 END) as expenses
            FROM transactions
            WHERE txn_date >= date('now','start of month')
        """).fetchone()

    def _pct(cur, base):
        if cur and base:
            return round((cur - base) / abs(base) * 100, 2)
        return 0.0

    lc  = latest["liquid_cash"]    if latest else 0
    inv = latest["invested_total"] if latest else 0
    eq  = latest["home_equity"]    if latest else 0

    return {
        "net_worth":     latest["net_worth"]    if latest else 0,
        "liquid_cash":   lc,
        "invested":      inv,
        "home_equity":   re["equity"]  if re else 0,
        "home_value":    re["value"]   if re else 0,
        "mortgage":      re["debt"]    if re else 0,
        "mom_change_pct":       _pct(latest["net_worth"] if latest else 0, prev["net_worth"]    if prev else None),
        "ytd_change_pct":       _pct(latest["net_worth"] if latest else 0, ytd_start["net_worth"] if ytd_start else None),
        "liquid_cash_mom_pct":  _pct(lc,  prev["liquid_cash"]    if prev else None),
        "liquid_cash_ytd_pct":  _pct(lc,  ytd_start["liquid_cash"]    if ytd_start else None),
        "invested_mom_pct":     _pct(inv, prev["invested_total"] if prev else None),
        "invested_ytd_pct":     _pct(inv, ytd_start["invested_total"] if ytd_start else None),
        "equity_mom_pct":       _pct(eq,  prev["home_equity"]    if prev else None),
        "equity_ytd_pct":       _pct(eq,  ytd_start["home_equity"]    if ytd_start else None),
        "income_mtd":    cashflow["income"]    if cashflow else 0,
        "expenses_mtd":  cashflow["expenses"]  if cashflow else 0,
        "history": [dict(r) for r in history],
    }


def get_allocation() -> dict:
    with get_conn() as conn:
        prices = {
            r["symbol"]: r["price"]
            for r in conn.execute("""
                SELECT symbol, price FROM prices p1
                WHERE recorded_at = (
                    SELECT MAX(recorded_at) FROM prices p2 WHERE p2.symbol=p1.symbol
                )
            """).fetchall()
        }

        holdings = conn.execute("""
            SELECT h.*, a.type as account_type
            FROM holdings h JOIN accounts a ON h.account_id=a.id
            WHERE a.is_active=1
        """).fetchall()

        targets = {
            r["asset_class"]: r["target_pct"]
            for r in conn.execute("SELECT * FROM allocation_targets").fetchall()
        }

    actual: dict[str, float] = {}
    total_invested = 0.0
    holding_rows = []

    for h in holdings:
        price = prices.get(h["symbol"], 0)
        market_value = h["shares"] * price
        cost = h["shares"] * (h["cost_basis"] or 0)
        gain = market_value - cost
        gain_pct = (gain / cost * 100) if cost else 0

        actual[h["asset_class"]] = actual.get(h["asset_class"], 0) + market_value
        total_invested += market_value

        holding_rows.append({
            "symbol":       h["symbol"],
            "name":         h["name"],
            "asset_class":  h["asset_class"],
            "shares":       h["shares"],
            "price":        price,
            "market_value": round(market_value, 2),
            "cost_basis":   round(cost, 2),
            "gain":         round(gain, 2),
            "gain_pct":     round(gain_pct, 2),
            "account_type": h["account_type"],
        })

    holding_rows.sort(key=lambda x: x["market_value"], reverse=True)

    classes = list(set(list(actual.keys()) + list(targets.keys())))
    allocation = []
    for cls in classes:
        mv = actual.get(cls, 0)
        actual_pct = (mv / total_invested * 100) if total_invested else 0
        target_pct = targets.get(cls, 0)
        allocation.append({
            "asset_class": cls,
            "market_value": round(mv, 2),
            "actual_pct":  round(actual_pct, 2),
            "target_pct":  target_pct,
            "drift":       round(actual_pct - target_pct, 2),
        })

    allocation.sort(key=lambda x: x["market_value"], reverse=True)

    return {
        "total_invested": round(total_invested, 2),
        "allocation": allocation,
        "holdings": holding_rows,
    }


def get_tax_opportunities() -> list[dict]:
    with get_conn() as conn:
        prices = {
            r["symbol"]: r["price"]
            for r in conn.execute("""
                SELECT symbol, price FROM prices p1
                WHERE recorded_at = (
                    SELECT MAX(recorded_at) FROM prices p2 WHERE p2.symbol=p1.symbol
                )
            """).fetchall()
        }
        holdings = conn.execute("""
            SELECT h.*, a.type as account_type
            FROM holdings h JOIN accounts a ON h.account_id=a.id
            WHERE a.type IN ('brokerage') AND a.is_active=1
        """).fetchall()

    opportunities = []
    for h in holdings:
        price = prices.get(h["symbol"], 0)
        cost = h["shares"] * (h["cost_basis"] or 0)
        market_value = h["shares"] * price
        gain = market_value - cost
        if gain < -500:  # only meaningful losses
            opportunities.append({
                "symbol":       h["symbol"],
                "name":         h["name"],
                "market_value": round(market_value, 2),
                "cost_basis":   round(cost, 2),
                "unrealized_loss": round(gain, 2),
            })

    return sorted(opportunities, key=lambda x: x["unrealized_loss"])


def get_journal(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM journal_entries
            ORDER BY entry_date DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_cashflow_by_category() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT
                b.name,
                b.monthly_target,
                b.direction,
                COALESCE(SUM(t.amount), 0) as actual
            FROM budget_categories b
            LEFT JOIN transactions t ON t.category=b.name
                AND t.txn_date >= date('now','start of month')
                AND t.direction = b.direction
            GROUP BY b.id
            ORDER BY b.direction, b.monthly_target DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_accounts_summary() -> list[dict]:
    with get_conn() as conn:
        accounts = conn.execute("""
            SELECT a.*,
                   s.balance
            FROM accounts a
            LEFT JOIN account_snapshots s ON s.account_id=a.id
                AND s.snapshot_id=(SELECT id FROM snapshots ORDER BY snapshot_date DESC LIMIT 1)
            WHERE a.is_active=1
            ORDER BY a.type, a.name
        """).fetchall()
    return [dict(r) for r in accounts]


def get_amortization(property_id: int) -> dict | None:
    """Return mortgage config + full schedule computed in Python."""
    with get_conn() as conn:
        cfg = conn.execute(
            "SELECT * FROM mortgage_config WHERE property_id=?", (property_id,)
        ).fetchone()
        if not cfg:
            return None
        costs = {
            (r["cost_year"], r["cost_month"]): dict(r)
            for r in conn.execute(
                "SELECT * FROM property_costs WHERE property_id=? ORDER BY cost_year,cost_month",
                (property_id,),
            ).fetchall()
        }

    cfg = dict(cfg)
    monthly_rate = cfg["annual_rate_pct"] / 100 / 12
    monthly_appr = (1 + cfg["appreciation_rate"] / 100) ** (1 / 12) - 1

    # Parse start date
    from datetime import date as _date
    start = _date.fromisoformat(cfg["start_date"])

    balance = cfg["loan_amount"]
    home_value = None  # will be set from real_estate table
    schedule = []

    for i in range(cfg["term_months"]):
        month_num = i + 1
        year  = start.year  + (start.month - 1 + i) // 12
        month = (start.month - 1 + i) % 12 + 1

        interest = balance * monthly_rate
        principal = cfg["monthly_payment"] - interest
        if principal > balance:
            principal = balance
        balance = max(0, balance - principal)

        # Estimate home value via appreciation
        if i == 0:
            # Anchor: use the loan amount + typical down payment is unknown,
            # so we approximate starting value as loan_amount / 0.8 (80% LTV),
            # but we'll let the frontend/user see relative appreciation.
            # Store index=1.0 at month 0 and multiply.
            home_value = cfg["loan_amount"] / 0.8  # rough anchor
        home_value *= (1 + monthly_appr)
        equity = home_value - balance

        cost_row = costs.get((year, month), {})

        schedule.append({
            "month":     month_num,
            "year":      year,
            "mo":        month,
            "payment":   round(cfg["monthly_payment"], 2),
            "principal": round(principal, 2),
            "interest":  round(interest, 2),
            "balance":   round(balance, 2),
            "home_value": round(home_value, 2),
            "equity":    round(equity, 2),
            "cost_amount": cost_row.get("amount", 0),
            "cost_memo":   cost_row.get("memo", ""),
            "cost_id":     cost_row.get("id"),
        })

    total_paid     = cfg["monthly_payment"] * cfg["term_months"]
    total_interest = total_paid - cfg["loan_amount"]

    return {
        "config": cfg,
        "schedule": schedule,
        "summary": {
            "total_paid":     round(total_paid, 2),
            "total_interest": round(total_interest, 2),
            "total_principal": round(cfg["loan_amount"], 2),
        },
    }


def get_real_estate() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM real_estate").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["equity"] = d["estimated_value"] - d["mortgage_balance"]
        d["ltv"] = round(d["mortgage_balance"] / d["estimated_value"] * 100, 1) if d["estimated_value"] else 0
        d["gain"] = d["estimated_value"] - d["purchase_price"]
        out.append(d)
    return out


def get_allocation_targets() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM allocation_targets ORDER BY asset_class").fetchall()
    return [dict(r) for r in rows]


def get_budget_categories_full() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM budget_categories ORDER BY direction, name"
        ).fetchall()
    return [dict(r) for r in rows]


_INDEX_LABELS = {
    'SPY': 'S&P 500',
    'QQQ': 'NASDAQ 100',
    'DIA': 'Dow 30',
    'IWM': 'Russell 2000',
    'GLD': 'Gold',
    'TLT': '20Y Treasury',
    'BTC-USD': 'Bitcoin',
}


def get_ticker_data() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p1.symbol,
                   p1.price        AS price,
                   p1.prev_close   AS prev_close,
                   p1.recorded_at  AS recorded_at,
                   p2.price        AS prev_price
            FROM prices p1
            LEFT JOIN prices p2 ON p2.symbol = p1.symbol
              AND p2.recorded_at = (
                  SELECT MAX(p3.recorded_at) FROM prices p3
                  WHERE p3.symbol = p1.symbol
                    AND p3.recorded_at < p1.recorded_at
              )
            WHERE p1.recorded_at = (
                SELECT MAX(p4.recorded_at) FROM prices p4
                WHERE p4.symbol = p1.symbol
            )
        """).fetchall()

        holding_symbols = {
            r[0] for r in conn.execute("SELECT DISTINCT symbol FROM holdings").fetchall()
        }

    price_map = {r['symbol']: dict(r) for r in rows}

    def make_item(symbol: str, label: str, is_index: bool) -> dict | None:
        if symbol not in price_map:
            return None
        d = price_map[symbol]
        price = d['price']
        # Prefer yfinance daily prev_close; fall back to last stored price
        prev = d['prev_close'] or d['prev_price']
        change = round(price - prev, 4) if prev else None
        change_pct = round((price - prev) / prev * 100, 2) if prev else None
        return {
            'symbol': symbol,
            'label': label,
            'price': round(price, 2),
            'change': change,
            'change_pct': change_pct,
            'is_index': is_index,
            'as_of': d['recorded_at'],
        }

    result = []
    for sym, label in _INDEX_LABELS.items():
        item = make_item(sym, label, True)
        if item:
            result.append(item)
    for sym in sorted(holding_symbols):
        item = make_item(sym, sym, False)
        if item:
            result.append(item)
    return result


def get_account_by_id(account_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("""
            SELECT a.*,
                   s.balance
            FROM accounts a
            LEFT JOIN account_snapshots s ON s.account_id = a.id
                AND s.snapshot_id = (SELECT id FROM snapshots ORDER BY snapshot_date DESC LIMIT 1)
            WHERE a.id = ?
        """, (account_id,)).fetchone()
    return dict(row) if row else None


def get_account_transactions(account_id: int, limit: int = 500) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM transactions
            WHERE account_id = ?
            ORDER BY txn_date DESC, id DESC
            LIMIT ?
        """, (account_id, limit)).fetchall()
    return [dict(r) for r in rows]


def get_transactions(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT t.*, a.name as account_name
            FROM transactions t
            LEFT JOIN accounts a ON a.id = t.account_id
            ORDER BY t.txn_date DESC, t.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]
