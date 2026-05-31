from __future__ import annotations

from app.csv_mapper import detect_transaction_csv_mapping


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
