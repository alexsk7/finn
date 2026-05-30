import pytest

from app.queries import get_dashboard_summary


def test_dashboard_summary_uses_live_balances_and_excludes_linked_mortgage_debt(minimal_seed_data):
    summary = get_dashboard_summary()

    assert summary["liquid_cash"] == pytest.approx(6800.0)
    assert summary["invested"] == pytest.approx(3010.0)
    assert summary["home_equity"] == pytest.approx(198800.0)

    # Linked loan account is already reflected in home equity and should not
    # also appear in debt_total.
    assert summary["debt_total"] == pytest.approx(0.0)

    assert summary["net_worth"] == pytest.approx(208610.0)
    assert summary["mom_change_pct"] == pytest.approx(4.3)


def test_dashboard_summary_contains_expected_history_shape(minimal_seed_data):
    summary = get_dashboard_summary()

    assert "history" in summary
    assert len(summary["history"]) >= 1
    latest = summary["history"][-1]

    expected_keys = {
        "snapshot_date",
        "net_worth",
        "liquid_cash",
        "invested_total",
        "home_equity",
        "debt_total",
        "other_assets",
    }
    assert expected_keys.issubset(latest.keys())
