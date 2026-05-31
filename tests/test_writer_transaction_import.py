from __future__ import annotations

import app.csv_mapper as csv_mapper
from app.writer import import_transaction_csv


def test_import_concatenates_description_and_memo(db_conn):
    csv_text = """transaction_date,amount,direction,category,description,memo
2026-05-01,-12.50,debit,food,Coffee,AM run
"""

    mapping = {
        "date": "transaction_date",
        "amount": "amount",
        "direction": "direction",
        "category": "category",
        "description": "description",
        "memo": "memo",
    }

    result = import_transaction_csv(csv_text, field_mapping=mapping)
    assert result["inserted"] == 1

    row = db_conn.execute(
        "SELECT txn_date, amount, direction, category, description FROM transactions ORDER BY id DESC LIMIT 1"
    ).fetchone()

    assert row is not None
    assert row["txn_date"] == "2026-05-01"
    assert row["amount"] == 12.5
    assert row["direction"] == "expense"
    assert row["category"] == "food"
    assert row["description"] == "Coffee | AM run"


def test_import_with_variant_headers_uses_detected_mapping(db_conn):
    csv_text = """Txn Dt,Posted On,Narration,Category,Txn Type,Value USD,Memo Text
05/01/2026,05/02/2026,Coffee,food,debit,-12.50,AM run
"""

    result = import_transaction_csv(csv_text)
    assert result["inserted"] == 1
    assert result["skipped"] == 0

    row = db_conn.execute(
        "SELECT txn_date, amount, direction, category, description FROM transactions ORDER BY id DESC LIMIT 1"
    ).fetchone()

    assert row is not None
    assert row["txn_date"] == "2026-05-01"
    assert row["amount"] == 12.5
    assert row["direction"] == "expense"
    assert row["category"] == "food"


def test_import_accepts_parenthesized_negative_amount(db_conn):
    csv_text = """transaction_date,amount,direction,category,description
2026-05-01,(12.50),debit,food,Coffee
"""

    result = import_transaction_csv(csv_text)
    assert result["inserted"] == 1
    assert result["skipped"] == 0

    row = db_conn.execute("SELECT amount, direction FROM transactions ORDER BY id DESC LIMIT 1").fetchone()

    assert row is not None
    assert row["amount"] == 12.5
    assert row["direction"] == "expense"


def test_import_accepts_parenthesized_negative_amount_with_currency_and_commas(db_conn):
    csv_text = """transaction_date,amount,direction,category,description
2026-05-01,"($1,234.50)",debit,food,Coffee
"""

    result = import_transaction_csv(csv_text)
    assert result["inserted"] == 1
    assert result["skipped"] == 0

    row = db_conn.execute("SELECT amount, direction FROM transactions ORDER BY id DESC LIMIT 1").fetchone()

    assert row is not None
    assert row["amount"] == 1234.5
    assert row["direction"] == "expense"


def test_import_fails_when_required_confidence_below_medium(init_schema):
    csv_text = """alpha,beta
not-a-date,not-a-number
"""

    result = import_transaction_csv(csv_text)

    assert result["inserted"] == 0
    assert result["skipped"] == 0
    assert result["total"] == 0
    assert result.get("warning")
    assert "below medium" in result["warning"].lower()
    assert result["errors"]


def test_import_transaction_csv_uses_post_date_fallback_for_missing_primary_date(db_conn):
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

    rows = db_conn.execute("SELECT txn_date, amount, direction FROM transactions ORDER BY id DESC LIMIT 3").fetchall()

    assert [r["txn_date"] for r in rows][::-1] == ["2026-05-01", "2026-05-03", "2026-05-04"]
    assert [r["amount"] for r in rows][::-1] == [10.0, 11.0, 12.0]
    assert all(r["direction"] == "expense" for r in rows)


def test_import_transaction_csv_detected_mapping_uses_post_date_fallback(db_conn):
    csv_text = """Transaction Date,Post Date,Amount,Description
2026-05-01,2026-05-02,-10.00,Coffee
,2026-05-03,-11.00,Groceries
2026-05-04,2026-05-05,-12.00,Transit
"""

    result = import_transaction_csv(csv_text)

    assert result["inserted"] == 3
    assert result["skipped"] == 0

    rows = db_conn.execute("SELECT txn_date, amount, direction FROM transactions ORDER BY id DESC LIMIT 3").fetchall()

    assert [r["txn_date"] for r in rows][::-1] == ["2026-05-01", "2026-05-03", "2026-05-04"]
    assert [r["amount"] for r in rows][::-1] == [10.0, 11.0, 12.0]
    assert all(r["direction"] == "expense" for r in rows)


def test_import_transaction_csv_account_id_param_overrides_csv_value(minimal_seed_data, db_conn):
    csv_text = """date,amount,account_id
2026-05-01,25.00,2
"""

    result = import_transaction_csv(csv_text, account_id=1)

    assert result["inserted"] == 1
    assert result["skipped"] == 0

    row = db_conn.execute("SELECT account_id FROM transactions ORDER BY id DESC LIMIT 1").fetchone()

    assert row is not None
    assert row["account_id"] == 1


def test_import_transaction_csv_infers_direction_from_amount_sign(db_conn):
    csv_text = """date,amount
2026-05-01,-25.00
2026-05-02,30.00
"""

    result = import_transaction_csv(csv_text)

    assert result["inserted"] == 2
    assert result["skipped"] == 0

    rows = db_conn.execute("SELECT txn_date, direction, amount FROM transactions ORDER BY id DESC LIMIT 2").fetchall()

    ordered = list(rows)[::-1]
    assert ordered[0]["txn_date"] == "2026-05-01"
    assert ordered[0]["direction"] == "expense"
    assert ordered[0]["amount"] == 25.0
    assert ordered[1]["txn_date"] == "2026-05-02"
    assert ordered[1]["direction"] == "income"
    assert ordered[1]["amount"] == 30.0


def test_import_explicit_field_mapping_bypasses_detector_confidence_gate(db_conn, monkeypatch):
    csv_text = """date,amount
2026-05-01,-25.00
"""

    def _low_confidence_detector(_csv_text: str):
        return {
            "ok": False,
            "delimiter": ",",
            "confidence": {"date": 0.0, "amount": 0.0},
        }

    monkeypatch.setattr(csv_mapper, "detect_transaction_csv_mapping", _low_confidence_detector)

    result = import_transaction_csv(
        csv_text,
        field_mapping={
            "date": "date",
            "amount": "amount",
        },
    )

    assert result["inserted"] == 1
    assert result["skipped"] == 0

    row = db_conn.execute("SELECT txn_date, amount, direction FROM transactions ORDER BY id DESC LIMIT 1").fetchone()

    assert row is not None
    assert row["txn_date"] == "2026-05-01"
    assert row["amount"] == 25.0
    assert row["direction"] == "expense"
