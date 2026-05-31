from __future__ import annotations

from app.csv_mapper import _best_delimiter_fallback, _profile_column, detect_transaction_csv_mapping


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


def test_profile_column_median_abs_even_count():
    profile = _profile_column(["1", "3", "5", "7"])
    assert profile.median_abs == 4.0


def test_profile_column_median_abs_odd_count():
    profile = _profile_column(["1", "3", "5"])
    assert profile.median_abs == 3.0


def test_detect_ignores_leading_comment_prologue():
    csv_text = """# Exported by Example Bank
# Account ending 1234
date,amount,description
2026-05-01,-10.00,Coffee
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert res["mapping"]["date"] == "date"
    assert res["mapping"]["amount"] == "amount"


def test_detect_preserves_hash_prefixed_data_rows_in_preview():
    csv_text = """date,amount,description
#2026-05-01,-10.00,hash row
2026-05-02,-12.00,normal row
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert len(res["preview"]) == 2
    assert res["preview"][0]["date"] == "#2026-05-01"


def test_best_delimiter_fallback_handles_quoted_commas_in_semicolon_csv():
    lines = [
        '"name, desc";"value"',
        '"foo, bar";"100"',
    ]

    assert _best_delimiter_fallback(lines) == ";"


def test_detect_uses_quote_aware_fallback_when_sniffer_fails(monkeypatch):
    import csv as _csv

    def _raise_sniffer_error(*args, **kwargs):
        raise _csv.Error("forced sniff failure")

    monkeypatch.setattr("app.csv_mapper.csv.Sniffer.sniff", _raise_sniffer_error)

    csv_text = 'Txn Dt;Value USD;Narration\n"05/01/2026";"-12.50";"Coffee, shop"\n'
    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert res["delimiter"] == ";"
    assert "date" in res["mapping"]
    assert "amount" in res["mapping"]
