"""All read queries used by the API routes."""

import re
from datetime import date

from .db import get_conn

_INVESTMENT_TYPES = {"brokerage", "retirement_401k", "retirement_ira", "hsa", "crypto"}
_DEBT_TYPES = {"credit", "loan"}
_CASH_TYPES = {"checking", "savings"}
_OTHER_TYPES = {"other"}
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _month_info(month: str | None = None) -> dict:
    m = (month or date.today().strftime("%Y-%m")).strip()
    if not _MONTH_RE.match(m):
        raise ValueError("Month must use YYYY-MM format")
    year, month_num = (int(p) for p in m.split("-", 1))
    if month_num < 1 or month_num > 12:
        raise ValueError("Month must be between 01 and 12")

    next_year = year + 1 if month_num == 12 else year
    next_num = 1 if month_num == 12 else month_num + 1
    prev_year = year - 1 if month_num == 1 else year
    prev_num = 12 if month_num == 1 else month_num - 1

    return {
        "month": f"{year:04d}-{month_num:02d}",
        "start": f"{year:04d}-{month_num:02d}-01",
        "end": f"{next_year:04d}-{next_num:02d}-01",
        "previous_month": f"{prev_year:04d}-{prev_num:02d}",
        "next_month": f"{next_year:04d}-{next_num:02d}",
    }


def _compute_balances(conn) -> dict[int, float]:
    """Compute current balance for every active account from live data sources.

    Investment accounts: holdings × latest price.
    Debt accounts (credit/loan): opening_balance + net spending (expenses − income).
    Cash accounts (checking/savings/other): opening_balance + net inflows (income − expenses).
    """
    accounts = conn.execute(
        "SELECT id, type, COALESCE(opening_balance, 0) as opening_balance FROM accounts WHERE is_active=1"
    ).fetchall()

    txn_rows = conn.execute("""
        SELECT account_id,
               COALESCE(SUM(CASE WHEN direction='income'  THEN amount ELSE 0 END), 0) AS income,
               COALESCE(SUM(CASE WHEN direction='expense' THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE account_id IS NOT NULL
        GROUP BY account_id
    """).fetchall()
    txn = {r["account_id"]: r for r in txn_rows}

    holding_rows = conn.execute("""
        SELECT h.account_id, COALESCE(SUM(h.shares * p.price), 0) AS market_value
        FROM holdings h
        LEFT JOIN prices p ON p.symbol = h.symbol
            AND p.recorded_at = (SELECT MAX(recorded_at) FROM prices p2 WHERE p2.symbol = h.symbol)
        GROUP BY h.account_id
    """).fetchall()
    holdings = {r["account_id"]: r["market_value"] for r in holding_rows}

    result: dict[int, float] = {}
    for a in accounts:
        aid = a["id"]
        opening = a["opening_balance"]
        t = txn.get(aid)
        if a["type"] in _INVESTMENT_TYPES:
            result[aid] = holdings.get(aid, 0)
        elif a["type"] in _DEBT_TYPES:
            result[aid] = opening + ((t["expense"] - t["income"]) if t else 0)
        else:
            result[aid] = opening + ((t["income"] - t["expense"]) if t else 0)
    return result


def get_dashboard_summary() -> dict:
    with get_conn() as conn:
        # Historical baselines — still from snapshots for MoM/YTD comparisons
        prev = conn.execute("""
            SELECT net_worth, liquid_cash, invested_total, home_equity
            FROM snapshots ORDER BY snapshot_date DESC LIMIT 1
        """).fetchone()

        ytd_start = conn.execute("""
            SELECT net_worth, liquid_cash, invested_total, home_equity FROM snapshots
            WHERE snapshot_date <= date('now','start of year')
            ORDER BY snapshot_date DESC LIMIT 1
        """).fetchone()

        history = conn.execute("""
            SELECT snapshot_date, net_worth, liquid_cash, invested_total, home_equity, debt_total,
                   COALESCE(other_assets, 0) as other_assets
            FROM snapshots ORDER BY snapshot_date ASC
        """).fetchall()

        re_rows = conn.execute("SELECT estimated_value, mortgage_balance, account_id FROM real_estate").fetchall()

        cashflow = conn.execute("""
            SELECT
                SUM(CASE WHEN direction='income'  THEN amount ELSE 0 END) as income,
                SUM(CASE WHEN direction='expense' THEN amount ELSE 0 END) as expenses
            FROM transactions
            WHERE txn_date >= date('now','start of month')
        """).fetchone()

        accounts = conn.execute(
            "SELECT id, name, type, interest_rate, minimum_payment FROM accounts WHERE is_active=1"
        ).fetchall()
        balances = _compute_balances(conn)

    # Loan accounts linked to a property are excluded from debt_total —
    # their balance is already captured as a reduction in home_equity.
    linked_mortgage_ids = {r["account_id"] for r in re_rows if r["account_id"]}

    re_value = sum(r["estimated_value"] for r in re_rows)
    re_mortgage = sum(
        balances.get(r["account_id"], r["mortgage_balance"]) if r["account_id"] else r["mortgage_balance"]
        for r in re_rows
    )
    home_equity = re_value - re_mortgage

    invested = sum(balances.get(a["id"], 0) for a in accounts if a["type"] in _INVESTMENT_TYPES)
    liquid_cash = sum(balances.get(a["id"], 0) for a in accounts if a["type"] in _CASH_TYPES)
    other_assets = sum(balances.get(a["id"], 0) for a in accounts if a["type"] in _OTHER_TYPES)
    debt_total = sum(
        balances.get(a["id"], 0) for a in accounts if a["type"] in _DEBT_TYPES and a["id"] not in linked_mortgage_ids
    )
    net_worth = invested + liquid_cash + home_equity + other_assets - debt_total

    liabilities = [
        {
            "id": a["id"],
            "name": a["name"],
            "type": a["type"],
            "interest_rate": a["interest_rate"],
            "minimum_payment": a["minimum_payment"],
            "balance": balances.get(a["id"], 0),
        }
        for a in accounts
        if a["type"] in _DEBT_TYPES and a["id"] not in linked_mortgage_ids
    ]

    def _pct(cur, base):
        if cur and base:
            return round((cur - base) / abs(base) * 100, 2)
        return 0.0

    return {
        "net_worth": net_worth,
        "liquid_cash": liquid_cash,
        "invested": invested,
        "home_equity": home_equity,
        "home_value": re_value,
        "mortgage": re_mortgage,
        "mom_change_pct": _pct(net_worth, prev["net_worth"] if prev else None),
        "ytd_change_pct": _pct(net_worth, ytd_start["net_worth"] if ytd_start else None),
        "liquid_cash_mom_pct": _pct(liquid_cash, prev["liquid_cash"] if prev else None),
        "liquid_cash_ytd_pct": _pct(liquid_cash, ytd_start["liquid_cash"] if ytd_start else None),
        "invested_mom_pct": _pct(invested, prev["invested_total"] if prev else None),
        "invested_ytd_pct": _pct(invested, ytd_start["invested_total"] if ytd_start else None),
        "equity_mom_pct": _pct(home_equity, prev["home_equity"] if prev else None),
        "equity_ytd_pct": _pct(home_equity, ytd_start["home_equity"] if ytd_start else None),
        "income_mtd": cashflow["income"] if cashflow else 0,
        "expenses_mtd": cashflow["expenses"] if cashflow else 0,
        "debt_total": debt_total,
        "other_assets": other_assets,
        "liabilities": liabilities,
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
            r["asset_class"]: r["target_pct"] for r in conn.execute("SELECT * FROM allocation_targets").fetchall()
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

        holding_rows.append(
            {
                "symbol": h["symbol"],
                "name": h["name"],
                "asset_class": h["asset_class"],
                "shares": h["shares"],
                "price": price,
                "market_value": round(market_value, 2),
                "cost_basis": round(cost, 2),
                "gain": round(gain, 2),
                "gain_pct": round(gain_pct, 2),
                "account_type": h["account_type"],
                "is_manual": bool(h["is_manual"]),
            }
        )

    holding_rows.sort(key=lambda x: x["market_value"], reverse=True)

    classes = list(set(list(actual.keys()) + list(targets.keys())))
    allocation = []
    for cls in classes:
        mv = actual.get(cls, 0)
        actual_pct = (mv / total_invested * 100) if total_invested else 0
        target_pct = targets.get(cls, 0)
        allocation.append(
            {
                "asset_class": cls,
                "market_value": round(mv, 2),
                "actual_pct": round(actual_pct, 2),
                "target_pct": target_pct,
                "drift": round(actual_pct - target_pct, 2),
            }
        )

    allocation.sort(key=lambda x: x["market_value"], reverse=True)

    return {
        "total_invested": round(total_invested, 2),
        "allocation": allocation,
        "holdings": holding_rows,
    }


def get_tax_summary() -> dict:
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
            WHERE a.type = 'brokerage' AND a.is_active=1
        """).fetchall()

        ytd_rows = conn.execute("""
            SELECT t.category,
                   SUM(t.amount) AS total,
                   COUNT(*)      AS count
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            WHERE a.type IN ('brokerage','retirement_401k','retirement_ira','hsa','crypto')
              AND t.direction = 'income'
              AND t.txn_date >= date('now','start of year')
            GROUP BY t.category
            ORDER BY total DESC
        """).fetchall()

    tlh_candidates = []
    unrealized_total = 0.0

    for h in holdings:
        price = prices.get(h["symbol"], 0)
        cost = h["shares"] * (h["cost_basis"] or 0)
        market_value = h["shares"] * price
        gain = market_value - cost
        unrealized_total += gain
        if gain < -500:
            tlh_candidates.append(
                {
                    "symbol": h["symbol"],
                    "name": h["name"],
                    "market_value": round(market_value, 2),
                    "cost_basis": round(cost, 2),
                    "unrealized_loss": round(gain, 2),
                }
            )

    tlh_candidates.sort(key=lambda x: x["unrealized_loss"])
    breakdown = [dict(r) for r in ytd_rows]

    return {
        "tlh_candidates": tlh_candidates,
        "unrealized_total": round(unrealized_total, 2),
        "tlh_total": round(sum(c["unrealized_loss"] for c in tlh_candidates), 2),
        "ytd_income_total": round(sum(r["total"] for r in ytd_rows), 2),
        "ytd_income_breakdown": breakdown,
    }


def get_journal(limit: int = 100) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM journal_entries
            ORDER BY entry_date DESC LIMIT ?
        """,
            (limit,),
        ).fetchall()
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
        accounts = conn.execute("SELECT * FROM accounts WHERE is_active=1 ORDER BY type, name").fetchall()
        balances = _compute_balances(conn)
    result = []
    for a in accounts:
        d = dict(a)
        d["balance"] = round(balances.get(a["id"], 0), 2)
        result.append(d)
    return result


def get_amortization(property_id: int) -> dict | None:
    """Return mortgage config + full schedule computed in Python."""
    with get_conn() as conn:
        cfg = conn.execute("SELECT * FROM mortgage_config WHERE property_id=?", (property_id,)).fetchone()
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
        year = start.year + (start.month - 1 + i) // 12
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
        home_value *= 1 + monthly_appr
        equity = home_value - balance

        cost_row = costs.get((year, month), {})

        schedule.append(
            {
                "month": month_num,
                "year": year,
                "mo": month,
                "payment": round(cfg["monthly_payment"], 2),
                "principal": round(principal, 2),
                "interest": round(interest, 2),
                "balance": round(balance, 2),
                "home_value": round(home_value, 2),
                "equity": round(equity, 2),
                "cost_amount": cost_row.get("amount", 0),
                "cost_memo": cost_row.get("memo", ""),
                "cost_id": cost_row.get("id"),
            }
        )

    total_paid = cfg["monthly_payment"] * cfg["term_months"]
    total_interest = total_paid - cfg["loan_amount"]

    return {
        "config": cfg,
        "schedule": schedule,
        "summary": {
            "total_paid": round(total_paid, 2),
            "total_interest": round(total_interest, 2),
            "total_principal": round(cfg["loan_amount"], 2),
        },
    }


def get_real_estate() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM real_estate").fetchall()
        loan_accounts = {
            r["id"]: r["name"]
            for r in conn.execute("SELECT id, name FROM accounts WHERE type='loan' AND is_active=1").fetchall()
        }
        balances = _compute_balances(conn)
    out = []
    for r in rows:
        d = dict(r)
        linked_id = d.get("account_id")
        if linked_id and linked_id in balances:
            d["mortgage_balance"] = round(balances[linked_id], 2)
            d["linked_account_name"] = loan_accounts.get(linked_id)
        else:
            d["linked_account_name"] = None
        d["equity"] = d["estimated_value"] - d["mortgage_balance"]
        d["ltv"] = round(d["mortgage_balance"] / d["estimated_value"] * 100, 1) if d["estimated_value"] else 0
        d["gain"] = d["estimated_value"] - d["purchase_price"]
        out.append(d)
    return out


def get_allocation_targets() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM allocation_targets ORDER BY asset_class").fetchall()
    return [dict(r) for r in rows]


def get_rebalance(new_cash: float = 0.0) -> dict:
    _TAX_ADVANTAGED = {"retirement_401k", "retirement_ira", "hsa"}

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
            SELECT h.symbol, h.name, h.asset_class, h.shares,
                   COALESCE(h.cost_basis, 0) AS cost_basis,
                   a.name AS account_name, a.type AS account_type
            FROM holdings h
            JOIN accounts a ON h.account_id = a.id
            WHERE a.is_active = 1
        """).fetchall()
        targets = {
            r["asset_class"]: r["target_pct"]
            for r in conn.execute("SELECT asset_class, target_pct FROM allocation_targets").fetchall()
        }

    holding_data = []
    actual: dict[str, float] = {}
    total_invested = 0.0

    for h in holdings:
        price = prices.get(h["symbol"], 0)
        mv = h["shares"] * price
        cost = h["shares"] * h["cost_basis"]
        unrealized = mv - cost
        actual[h["asset_class"]] = actual.get(h["asset_class"], 0) + mv
        total_invested += mv
        holding_data.append(
            {
                "symbol": h["symbol"],
                "name": h["name"],
                "asset_class": h["asset_class"],
                "shares": h["shares"],
                "price": price,
                "mv": mv,
                "unrealized": unrealized,
                "account_name": h["account_name"],
                "account_type": h["account_type"],
            }
        )

    total_portfolio = total_invested + new_cash

    # Drift per asset class (positive = over-allocated, negative = under-allocated)
    all_classes = set(list(actual.keys()) + list(targets.keys()))
    drift: dict[str, float] = {}
    alloc_rows = []
    for cls in all_classes:
        actual_v = actual.get(cls, 0)
        tgt_pct = targets.get(cls, 0)
        tgt_v = total_portfolio * tgt_pct / 100 if total_portfolio > 0 else 0
        d = actual_v - tgt_v
        drift[cls] = d
        alloc_rows.append(
            {
                "asset_class": cls,
                "actual": round(actual_v, 2),
                "actual_pct": round(actual_v / total_invested * 100, 2) if total_invested else 0,
                "target_pct": tgt_pct,
                "target": round(tgt_v, 2),
                "drift": round(d, 2),
            }
        )
    alloc_rows.sort(key=lambda x: x["drift"], reverse=True)

    def _sell_priority(h):
        if h["account_type"] == "brokerage" and h["unrealized"] < -500:
            return 1  # TLH: harvest loss while rebalancing
        if h["account_type"] in _TAX_ADVANTAGED:
            return 2  # no tax consequence
        return 3  # taxable gain — last resort

    # Sell trades for over-allocated classes
    sell_trades = []
    for cls in all_classes:
        over_by = drift.get(cls, 0)
        if over_by <= 10:
            continue
        remaining = over_by
        class_holdings = sorted(
            [h for h in holding_data if h["asset_class"] == cls and h["price"] > 0],
            key=_sell_priority,
        )
        for h in class_holdings:
            if remaining < 10:
                break
            sell_v = min(h["mv"], remaining)
            acct_type = h["account_type"]
            unreal = h["unrealized"]
            if acct_type == "brokerage" and unreal < -500:
                tax_note = "TLH opportunity"
            elif acct_type in _TAX_ADVANTAGED:
                tax_note = "tax-free (IRA/401k)"
            elif acct_type == "brokerage" and unreal > 0:
                tax_note = "taxable gain"
            else:
                tax_note = ""
            sell_trades.append(
                {
                    "symbol": h["symbol"],
                    "name": h["name"],
                    "asset_class": cls,
                    "account_name": h["account_name"],
                    "account_type": acct_type,
                    "shares": round(sell_v / h["price"], 3),
                    "amount": round(sell_v, 2),
                    "unrealized": round(unreal, 2),
                    "tax_note": tax_note,
                }
            )
            remaining -= sell_v

    # Buy targets for under-allocated classes
    buy_targets = []
    for cls in all_classes:
        under_by = -drift.get(cls, 0)
        if under_by <= 10:
            continue
        class_holdings = [h for h in holding_data if h["asset_class"] == cls]
        # Suggest buying in taxable brokerage if possible (no buy-side tax), else any existing account
        preferred = next((h for h in class_holdings if h["account_type"] == "brokerage"), None) or (
            class_holdings[0] if class_holdings else None
        )
        seen = set()
        existing = []
        for h in class_holdings:
            key = (h["symbol"], h["account_name"])
            if key not in seen:
                seen.add(key)
                existing.append({"symbol": h["symbol"], "name": h["name"], "account_name": h["account_name"]})
        buy_targets.append(
            {
                "asset_class": cls,
                "amount_needed": round(under_by, 2),
                "suggested_account": preferred["account_name"] if preferred else None,
                "existing_symbols": existing,
            }
        )
    buy_targets.sort(key=lambda x: x["amount_needed"], reverse=True)

    _tax_order = {"TLH opportunity": 0, "tax-free (IRA/401k)": 1, "": 2, "taxable gain": 3}
    sell_trades.sort(key=lambda t: (_tax_order.get(t["tax_note"], 2), -t["amount"]))

    return {
        "total_portfolio": round(total_portfolio, 2),
        "total_invested": round(total_invested, 2),
        "new_cash": round(new_cash, 2),
        "allocation": alloc_rows,
        "sell_trades": sell_trades,
        "buy_targets": buy_targets,
        "total_sell": round(sum(t["amount"] for t in sell_trades), 2),
        "total_buy": round(sum(t["amount_needed"] for t in buy_targets), 2),
    }


def get_budget_categories_full() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM budget_categories ORDER BY direction, name").fetchall()
    return [dict(r) for r in rows]


def get_budget_month(month: str | None = None) -> dict:
    info = _month_info(month)
    with get_conn() as conn:
        month_row = conn.execute("SELECT * FROM budget_months WHERE month=?", (info["month"],)).fetchone()

        rows = conn.execute(
            """
            SELECT
                b.id AS category_id,
                b.name,
                b.direction,
                b.monthly_target AS default_target,
                COALESCE(bmi.planned_amount, 0) AS planned_amount,
                COALESCE(SUM(t.amount), 0) AS actual
            FROM budget_categories b
            LEFT JOIN budget_month_items bmi
              ON bmi.category_id = b.id AND bmi.month = ?
            LEFT JOIN transactions t
              ON t.category = b.name
             AND t.direction = b.direction
             AND t.txn_date >= ?
             AND t.txn_date < ?
            GROUP BY b.id
            ORDER BY b.direction, b.name
        """,
            (info["month"], info["start"], info["end"]),
        ).fetchall()

        uncategorized_rows = conn.execute(
            """
            SELECT direction,
                   COUNT(*) AS count,
                   COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE txn_date >= ?
              AND txn_date < ?
              AND LOWER(TRIM(COALESCE(category, ''))) IN ('', 'uncategorized')
            GROUP BY direction
        """,
            (info["start"], info["end"]),
        ).fetchall()

        unbudgeted_rows = conn.execute(
            """
            SELECT t.direction,
                   t.category,
                   COUNT(*) AS count,
                   COALESCE(SUM(t.amount), 0) AS total
            FROM transactions t
            WHERE t.txn_date >= ?
              AND t.txn_date < ?
              AND LOWER(TRIM(COALESCE(t.category, ''))) NOT IN ('', 'uncategorized')
              AND NOT EXISTS (
                  SELECT 1 FROM budget_categories b
                  WHERE b.name = t.category AND b.direction = t.direction
              )
            GROUP BY t.direction, t.category
            ORDER BY total DESC
        """,
            (info["start"], info["end"]),
        ).fetchall()

    categories = []
    totals = {
        "planned_income": 0.0,
        "planned_expense": 0.0,
        "actual_income": 0.0,
        "actual_expense": 0.0,
    }
    for row in rows:
        d = dict(row)
        planned = float(d["planned_amount"] or 0)
        actual = float(d["actual"] or 0)
        d["planned_amount"] = planned
        d["actual"] = actual
        d["variance"] = round(actual - planned, 2)
        if d["direction"] == "income":
            totals["planned_income"] += planned
            totals["actual_income"] += actual
        else:
            totals["planned_expense"] += planned
            totals["actual_expense"] += actual
        categories.append(d)

    uncategorized = {
        "income": {"count": 0, "total": 0.0},
        "expense": {"count": 0, "total": 0.0},
        "transfer": {"count": 0, "total": 0.0},
    }
    for row in uncategorized_rows:
        uncategorized[row["direction"]] = {
            "count": int(row["count"] or 0),
            "total": float(row["total"] or 0),
        }

    planned_net = totals["planned_income"] - totals["planned_expense"]
    actual_net = totals["actual_income"] - totals["actual_expense"]
    savings_rate = (actual_net / totals["actual_income"] * 100) if totals["actual_income"] else 0

    return {
        "month": info["month"],
        "previous_month": info["previous_month"],
        "next_month": info["next_month"],
        "exists": bool(month_row),
        "notes": month_row["notes"] if month_row else None,
        "categories": categories,
        "uncategorized": uncategorized,
        "unbudgeted": [dict(r) for r in unbudgeted_rows],
        "totals": {
            **{k: round(v, 2) for k, v in totals.items()},
            "planned_net": round(planned_net, 2),
            "actual_net": round(actual_net, 2),
            "left_to_assign": round(planned_net, 2),
            "savings_rate": round(savings_rate, 1),
        },
    }


_INDEX_LABELS = {
    "SPY": "S&P 500",
    "QQQ": "NASDAQ 100",
    "DIA": "Dow 30",
    "IWM": "Russell 2000",
    "GLD": "Gold",
    "TLT": "20Y Treasury",
    "BTC-USD": "Bitcoin",
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
            r[0] for r in conn.execute("SELECT DISTINCT symbol FROM holdings WHERE is_manual=0").fetchall()
        }

    price_map = {r["symbol"]: dict(r) for r in rows}

    def make_item(symbol: str, label: str, is_index: bool) -> dict | None:
        if symbol not in price_map:
            return None
        d = price_map[symbol]
        price = d["price"]
        # Prefer yfinance daily prev_close; fall back to last stored price
        prev = d["prev_close"] or d["prev_price"]
        change = round(price - prev, 4) if prev else None
        change_pct = round((price - prev) / prev * 100, 2) if prev else None
        return {
            "symbol": symbol,
            "label": label,
            "price": round(price, 2),
            "change": change,
            "change_pct": change_pct,
            "is_index": is_index,
            "as_of": d["recorded_at"],
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
        row = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if not row:
            return None
        balances = _compute_balances(conn)
    d = dict(row)
    d["balance"] = round(balances.get(account_id, 0), 2)
    return d


def get_account_transactions(account_id: int, limit: int = 500) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM transactions
            WHERE account_id = ?
            ORDER BY txn_date DESC, id DESC
            LIMIT ?
        """,
            (account_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_transactions(
    limit: int = 100,
    category: str | None = None,
    direction: str | None = None,
    account_id: int | None = None,
    month: str | None = None,
) -> list[dict]:
    limit = max(1, min(int(limit), 1000))
    where: list[str] = []
    params: list[object] = []

    if category:
        cat = category.strip()
        if cat.lower() == "uncategorized":
            where.append("LOWER(TRIM(COALESCE(t.category, ''))) IN ('', 'uncategorized')")
        else:
            where.append("t.category = ?")
            params.append(cat)

    if direction:
        where.append("t.direction = ?")
        params.append(direction)

    if account_id is not None:
        where.append("t.account_id = ?")
        params.append(account_id)

    if month:
        info = _month_info(month)
        where.extend(["t.txn_date >= ?", "t.txn_date < ?"])
        params.extend([info["start"], info["end"]])

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT t.*, a.name as account_name
            FROM transactions t
            LEFT JOIN accounts a ON a.id = t.account_id
            {where_sql}
            ORDER BY t.txn_date DESC, t.id DESC
            LIMIT ?
        """,
            (*params, limit),
        ).fetchall()
    return [dict(r) for r in rows]
