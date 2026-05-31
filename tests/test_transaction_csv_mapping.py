from __future__ import annotations

import pytest

from app.csv_mapper import detect_transaction_csv_mapping
from app.db import get_conn
from app.writer import import_transaction_csv


def test_detect_fuzzy_match_with_standard_headers():
    csv_text = """date,amount,direction,category,payee,description,memo
2026-05-01,-12.50,debit,food,Cafe,Coffee,AM run
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert res["strategy"] == "fuzzy_match"
    assert res["mapping"]["date"] == "date"
    assert res["mapping"]["amount"] == "amount"


def test_detect_fuzzy_match_with_variant_headers():
    csv_text = """Txn Dt,Posted On,Narration,Category,Txn Type,Value USD,Memo Text
05/01/2026,05/02/2026,Coffee,food,debit,-12.50,AM run
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert res["strategy"] == "fuzzy_match"
    assert "date" in res["mapping"]
    assert "amount" in res["mapping"]


def test_transaction_date_preferred_with_post_date_fallback():
    csv_text = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
2026-05-01,2026-05-02,Coffee,food,debit,-12.50,AM run
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert res["strategy"] == "fuzzy_match"
    assert res["mapping"]["date"] == "Transaction Date"
    assert res["mapping"].get("_date_fallback") == "Post Date"


def test_import_concatenates_description_and_memo(init_schema):
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

    with get_conn() as conn:
        row = conn.execute(
            "SELECT txn_date, amount, direction, category, description FROM transactions ORDER BY id DESC LIMIT 1"
        ).fetchone()

    assert row is not None
    assert row["txn_date"] == "2026-05-01"
    assert row["amount"] == 12.5
    assert row["direction"] == "expense"
    assert row["category"] == "food"
    assert row["description"] == "Coffee | AM run"
