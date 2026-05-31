from __future__ import annotations

import random

import pytest

from app.csv_mapper import (
    AMOUNT_MEDIAN_ABS_MAX,
    BOOL_TOKENS_LOWER,
    MAX_CSV_LINES,
    MAX_CSV_TEXT_CHARS,
    ColumnProfile,
    _adaptive_blend_weights,
    _best_delimiter_fallback,
    _maybe_model_probs,
    _parse_date,
    _parse_float,
    _profile_column,
    _profile_score,
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


def test_transaction_date_preferred_over_posted_date_when_primary_has_blanks():
    csv_text = """Transaction Date,Post Date,Amount,Description
2026-05-01,2026-05-02,-10.00,Coffee
,2026-05-03,-11.00,Groceries
2026-05-04,2026-05-05,-12.00,Transit
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
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


def test_detect_fails_when_required_fields_need_reused_header():
    csv_text = """Amount
-12.50
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is False
    assert "not enough distinct headers" in res["error"].lower()
    assert res["mapping"].get("amount") == "Amount"


def test_amount_profile_score_uses_configured_median_bounds():
    in_range = _profile_column(["10", "25", "35", "45"])
    out_of_range = _profile_column([str(AMOUNT_MEDIAN_ABS_MAX + 1), str(AMOUNT_MEDIAN_ABS_MAX + 2)])

    in_range_score = _profile_score("amount", in_range)
    out_of_range_score = _profile_score("amount", out_of_range)

    assert in_range_score > out_of_range_score


def test_detect_fails_when_header_exists_but_no_data_rows():
    csv_text = "date,amount,description\n"

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is False
    assert res["error"] == "No data rows found"
    assert res["headers"] == ["date", "amount", "description"]
    assert res["model"]["status"] == "skipped_no_data"


def test_parse_date_accepts_day_first_format():
    assert _parse_date("31/05/2026") is True


def test_parse_date_accepts_iso_datetime_z_suffix():
    assert _parse_date("2026-05-31T14:30:00Z") is True


def test_profile_column_direction_token_rate_includes_new_variants():
    profile = _profile_column(["inflow", "outflow", "payment", "receive", "other"])
    assert profile.direction_token_rate == 0.8


def test_detect_maps_direction_column_with_new_token_values():
    csv_text = """date,amount,movement,description
2026-05-01,-12.50,outflow,Coffee
2026-05-02,20.00,inflow,Refund
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    movement_profile = _profile_column(["outflow", "inflow"])
    desc_profile = _profile_column(["Coffee", "Refund"])
    assert _profile_score("direction", movement_profile) > _profile_score("direction", desc_profile)


def test_bool_tokens_lower_is_defensively_normalized():
    assert "true" in BOOL_TOKENS_LOWER
    assert "false" in BOOL_TOKENS_LOWER
    assert "yes" in BOOL_TOKENS_LOWER
    assert "no" in BOOL_TOKENS_LOWER


def test_detect_fails_for_oversized_csv_text():
    csv_text = "x" * (MAX_CSV_TEXT_CHARS + 1)

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is False
    assert "exceeds max size" in res["error"].lower()


def test_detect_fails_for_excessive_line_count():
    csv_text = ("x\n" * MAX_CSV_LINES) + "x"

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is False
    assert "exceeds max line count" in res["error"].lower()


def test_column_profile_validation_rejects_out_of_range_values():
    with pytest.raises(ValueError):
        ColumnProfile(
            null_rate=1.1,
            date_rate=0.0,
            numeric_rate=0.0,
            bool_rate=0.0,
            neg_rate=0.0,
            median_abs=0.0,
            mean_len=0.0,
            unique_ratio=0.0,
            direction_token_rate=0.0,
        )


def test_detect_handles_utf8_bom_header():
    csv_text = "\ufeffdate,amount,description\n2026-05-01,-12.50,Coffee\n"

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert "date" in res["mapping"]
    assert "amount" in res["mapping"]


def test_detect_handles_mismatched_row_lengths_without_crashing():
    csv_text = "date,amount,description\n2026-05-01,-12.50,Coffee\n2026-05-02,-8.00\n"

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert res["headers"] == ["date", "amount", "description"]


def test_detect_handles_very_wide_csv_headers():
    headers = [f"col{i}" for i in range(120)]
    rows = ["x" for _ in range(120)]
    csv_text = ",".join(headers) + "\n" + ",".join(rows) + "\n"

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert len(res["headers"]) == 120


def test_detect_handles_embedded_newline_in_quoted_field():
    csv_text = 'date,amount,description\n2026-05-01,-12.50,"Coffee\nShop"\n'

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert len(res["preview"]) == 1
    assert "Coffee" in res["preview"][0]["description"]


def test_parse_float_handles_mixed_currency_symbols():
    assert _parse_float("$100") == 100.0
    assert _parse_float("€50") == 50.0
    assert _parse_float("¥1000") == 1000.0


def test_parse_float_handles_multiple_negative_notations():
    assert _parse_float("(100)") == -100.0
    assert _parse_float("-100") == -100.0
    assert _parse_float("100-") == -100.0


def test_parse_float_handles_locale_thousands_separators():
    assert _parse_float("1,000.00") == 1000.0
    assert _parse_float("1.000,00") == 1000.0


def test_parse_float_handles_scientific_notation():
    assert _parse_float("1.23e4") == 12300.0


def test_parse_float_rejects_nan_and_infinity():
    assert _parse_float("NaN") is None
    assert _parse_float("Infinity") is None
    assert _parse_float("-inf") is None


def test_detect_handles_100_plus_columns_and_returns_model_meta():
    headers = ["date", "amount"] + [f"col{i}" for i in range(130)]
    row = ["2026-05-01", "-12.50"] + ["x" for _ in range(130)]
    csv_text = ",".join(headers) + "\n" + ",".join(row) + "\n"

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert "model" in res
    assert set(res["model"].keys()) == {"available", "status", "anchor_count", "class_count"}


def test_detect_handles_identical_rows_consistently():
    csv_text = """date,amount,description
2026-05-01,-12.50,Coffee
2026-05-01,-12.50,Coffee
2026-05-01,-12.50,Coffee
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert "date" in res["mapping"]
    assert "amount" in res["mapping"]
    assert "model" in res


def test_maybe_model_probs_reports_training_error(monkeypatch):
    sklearn_linear_model = pytest.importorskip("sklearn.linear_model")

    class FailingLogisticRegression:
        def __init__(self, *args, **kwargs):
            pass

        def fit(self, *args, **kwargs):
            raise RuntimeError("forced training failure")

    monkeypatch.setattr(sklearn_linear_model, "LogisticRegression", FailingLogisticRegression)

    profiles = {
        "h_date": ColumnProfile(0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 10.0, 0.5, 0.0),
        "h_amount": ColumnProfile(0.0, 0.0, 1.0, 0.0, 0.5, 50.0, 6.0, 0.5, 0.0),
    }
    header_scores = {
        "h_date": {
            field: (0.95 if field == "date" else 0.0)
            for field in [
                "date",
                "amount",
                "direction",
                "category",
                "payee",
                "description",
                "memo",
                "account_id",
                "recurring",
            ]
        },
        "h_amount": {
            field: (0.95 if field == "amount" else 0.0)
            for field in [
                "date",
                "amount",
                "direction",
                "category",
                "payee",
                "description",
                "memo",
                "account_id",
                "recurring",
            ]
        },
    }

    probs, meta = _maybe_model_probs(profiles, header_scores)

    assert meta["available"] is False
    assert meta["status"] == "skipped_training_error"
    assert meta["anchor_count"] == 2
    assert meta["class_count"] == 2
    assert probs["h_date"]["date"] == 0.0


def test_detect_randomized_header_variants_is_stable():
    rng = random.Random(20260531)
    date_headers = ["date", "transaction date", "txn dt", "posted on", "date_recorded"]
    amount_headers = ["amount", "value", "amt", "value usd", "debit credit"]
    desc_headers = ["description", "memo", "narration", "details", "note"]

    for _ in range(50):
        d_h = rng.choice(date_headers)
        a_h = rng.choice(amount_headers)
        x_h = rng.choice(desc_headers)

        # Vary row count and value shape while keeping required fields present.
        n_rows = rng.randint(1, 8)
        rows = []
        for i in range(n_rows):
            day = 1 + (i % 28)
            amount = -float(rng.randint(1, 500)) / 10.0
            desc = f"item-{rng.randint(100, 999)}"
            rows.append(f"2026-05-{day:02d},{amount:.2f},{desc}")

        csv_text = f"{d_h},{a_h},{x_h}\n" + "\n".join(rows) + "\n"
        res = detect_transaction_csv_mapping(csv_text)

        assert "ok" in res
        if res["ok"]:
            assert "date" in res["mapping"]
            assert "amount" in res["mapping"]
        else:
            # Valid for edge randomizations to require confirmation/fallback, but must be explicit.
            assert "error" in res


def test_detect_randomized_direction_token_profile_stability():
    rng = random.Random(8675309)
    direction_pool = ["debit", "credit", "inflow", "outflow", "payment", "receive"]

    for _ in range(40):
        values = [rng.choice(direction_pool) for _ in range(rng.randint(3, 12))]
        profile = _profile_column(values)
        # With all values from known direction token pool, token rate should be perfect.
        assert profile.direction_token_rate == 1.0


def test_detect_skips_only_leading_comments_not_hash_prefixed_data_rows():
    csv_text = """# export metadata
# generated at 2026-05-31
date,amount,description
#2026-05-01,-12.50,hash row
2026-05-02,-8.00,normal row
"""

    res = detect_transaction_csv_mapping(csv_text)

    assert res["ok"] is True
    assert len(res["preview"]) == 2
    assert res["preview"][0]["date"] == "#2026-05-01"
    assert res["preview"][1]["date"] == "2026-05-02"
