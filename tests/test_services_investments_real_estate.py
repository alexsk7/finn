from app.services import investments as inv_svc
from app.services import real_estate as re_svc


def test_investments_symbol_normalization_and_validated_wrappers(monkeypatch):
    assert inv_svc.normalize_holding_symbol(" vti ", False) == "VTI"
    assert inv_svc.normalize_holding_symbol(" m:custom ", True) == "M:CUSTOM"

    try:
        inv_svc.normalize_holding_symbol("VTI", True)
        assert False, "Expected ValueError for invalid manual symbol"
    except ValueError as e:
        assert "Manual holding symbols" in str(e)

    try:
        inv_svc.normalize_holding_symbol("M:CUSTOM", False)
        assert False, "Expected ValueError for invalid non-manual symbol"
    except ValueError as e:
        assert "Non-manual symbols" in str(e)

    monkeypatch.setattr("app.services.investments.add_holding", lambda *args: {"args": args})
    monkeypatch.setattr("app.services.investments.update_holding", lambda *args: {"args": args})

    added = inv_svc.add_holding_validated(1, " m:fund ", "other", 1, 1, "Fund", True)
    assert added["args"][1] == "M:FUND"

    updated = inv_svc.update_holding_validated(7, 1, " vti ", "us_equity", 2, 3, "ETF", False)
    assert updated["args"][2] == "VTI"


def test_real_estate_amortization_fallback_wrapper(monkeypatch):
    monkeypatch.setattr("app.services.real_estate.get_amortization", lambda property_id: None)
    assert re_svc.get_amortization_or_empty(1) == {"config": None, "schedule": [], "summary": {}}

    expected = {"config": {"property_id": 1}, "schedule": [{"month": 1}], "summary": {"paid": 100}}
    monkeypatch.setattr("app.services.real_estate.get_amortization", lambda property_id: expected)
    assert re_svc.get_amortization_or_empty(1) == expected