from __future__ import annotations

from app.db import get_conn
from app.writer import add_transaction, import_transaction_csv


def test_add_transaction_normalizes_blank_category(init_schema):
    result = add_transaction(
        txn_date="2026-05-10",
        amount=42.0,
        direction="expense",
        category="   ",
        payee="Coffee Shop",
        description="Latte",
    )

    assert result["category"] == "uncategorized"

    with get_conn() as conn:
        row = conn.execute(
            "SELECT category FROM transactions WHERE id=?",
            (result["id"],),
        ).fetchone()

    assert row is not None
    assert row["category"] == "uncategorized"


def test_import_transaction_csv_uses_post_date_fallback_for_missing_primary_date(init_schema):
    csv_text = """Transaction Date,Post Date,Amount
2026-05-01,2026-05-02,-10.00
,2026-05-03,-11.00
2026-05-04,2026-05-05,-12.00
"""

    mapping = {
        "date": "Transaction Date",
        "_date_fallback": "Post Date",
        "amount": "Amount",
    }

    result = import_transaction_csv(csv_text, field_mapping=mapping)

    assert result["inserted"] == 3
    assert result["skipped"] == 0

    with get_conn() as conn:
        rows = conn.execute("SELECT txn_date, amount, direction FROM transactions ORDER BY id DESC LIMIT 3").fetchall()

    assert [r["txn_date"] for r in rows][::-1] == ["2026-05-01", "2026-05-03", "2026-05-04"]
    assert [r["amount"] for r in rows][::-1] == [10.0, 11.0, 12.0]
    assert all(r["direction"] == "expense" for r in rows)


def test_import_transaction_csv_account_id_param_overrides_csv_value(init_schema, minimal_seed_data):
    csv_text = """date,amount,account_id
2026-05-01,25.00,2
"""

    result = import_transaction_csv(csv_text, account_id=1)

    assert result["inserted"] == 1
    assert result["skipped"] == 0

    with get_conn() as conn:
        row = conn.execute("SELECT account_id FROM transactions ORDER BY id DESC LIMIT 1").fetchone()

    assert row is not None
    assert row["account_id"] == 1


def test_import_transaction_csv_infers_direction_from_amount_sign(init_schema):
    csv_text = """date,amount
2026-05-01,-25.00
2026-05-02,30.00
"""

    result = import_transaction_csv(csv_text)

    assert result["inserted"] == 2
    assert result["skipped"] == 0

    with get_conn() as conn:
        rows = conn.execute("SELECT txn_date, direction, amount FROM transactions ORDER BY id DESC LIMIT 2").fetchall()

    ordered = list(rows)[::-1]
    assert ordered[0]["txn_date"] == "2026-05-01"
    assert ordered[0]["direction"] == "expense"
    assert ordered[0]["amount"] == 25.0
    assert ordered[1]["txn_date"] == "2026-05-02"
    assert ordered[1]["direction"] == "income"
    assert ordered[1]["amount"] == 30.0
