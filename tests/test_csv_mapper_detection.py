from __future__ import annotations

from app.csv_mapper import (
    _adaptive_blend_weights,
    _best_delimiter_fallback,
    _parse_float,
    _profile_column,
    detect_transaction_csv_mapping,
)


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


def test_parse_float_handles_currency_code_and_thousands():
    assert _parse_float("$1,234.56 USD") == 1234.56


def test_parse_float_handles_parenthesized_currency_negative():
    assert _parse_float("($1,234.56)") == -1234.56


def test_parse_float_handles_european_decimal_format():
    assert _parse_float("(€1.234,50)") == -1234.5


def test_adaptive_blend_weights_sum_to_one_without_model():
    header_w, profile_w, model_w = _adaptive_blend_weights(0.8, 0.4, 0.0, model_available=False)
    assert round(header_w + profile_w + model_w, 10) == 1.0
    assert model_w == 0.0


def test_adaptive_blend_weights_shift_with_header_strength():
    low_header_w, _, _ = _adaptive_blend_weights(0.2, 0.6, 0.0, model_available=False)
    high_header_w, _, _ = _adaptive_blend_weights(0.9, 0.6, 0.0, model_available=False)
    assert high_header_w > low_header_w


def test_adaptive_blend_weights_uses_model_when_available():
    _, _, low_model_w = _adaptive_blend_weights(0.6, 0.6, 0.1, model_available=True)
    _, _, high_model_w = _adaptive_blend_weights(0.6, 0.6, 0.9, model_available=True)
    assert high_model_w > low_model_w


def test_adaptive_blend_weights_shift_with_profile_strength():
    _, low_profile_w, _ = _adaptive_blend_weights(0.7, 0.1, 0.0, model_available=False)
    _, high_profile_w, _ = _adaptive_blend_weights(0.7, 0.9, 0.0, model_available=False)
    assert high_profile_w > low_profile_w


def test_detect_exposes_model_status_metadata():
    csv_text = """Txn Dt,Posted On,Narration,Category,Txn Type,Value USD,Memo Text
05/01/2026,05/02/2026,Coffee,food,debit,-12.50,AM run
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert "model" in res
    model = res["model"]
    assert set(model.keys()) == {"available", "status", "anchor_count", "class_count"}
    assert isinstance(model["available"], bool)
    assert isinstance(model["anchor_count"], int)
    assert isinstance(model["class_count"], int)
    assert model["status"] in {
        "trained",
        "skipped_no_sklearn",
        "skipped_insufficient_anchors",
        "skipped_training_error",
    }
