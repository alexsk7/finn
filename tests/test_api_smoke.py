from fastapi.testclient import TestClient


def test_api_dashboard_accounts_allocation_smoke(import_main_safely, minimal_seed_data):
    client = TestClient(import_main_safely.app)

    dash = client.get("/api/dashboard")
    assert dash.status_code == 200
    dashboard = dash.json()
    assert "net_worth" in dashboard
    assert "history" in dashboard

    accounts = client.get("/api/accounts")
    assert accounts.status_code == 200
    accounts_payload = accounts.json()
    assert isinstance(accounts_payload, list)
    assert len(accounts_payload) >= 1

    allocation = client.get("/api/allocation")
    assert allocation.status_code == 200
    allocation_payload = allocation.json()
    assert "allocation" in allocation_payload
    assert "holdings" in allocation_payload


def test_api_price_refresh_smoke(import_main_safely, minimal_seed_data, mock_yfinance_ticker):
    client = TestClient(import_main_safely.app)

    mock_yfinance_ticker.set_fast("VTI", last_price=271.0, previous_close=270.0)
    mock_yfinance_ticker.set_fast("VXUS", last_price=63.0, previous_close=62.0)

    response = client.post("/api/prices/refresh")
    assert response.status_code == 200

    payload = response.json()
    assert "updated" in payload
    assert "failed" in payload
    assert any(item["symbol"] == "VTI" for item in payload["updated"])
