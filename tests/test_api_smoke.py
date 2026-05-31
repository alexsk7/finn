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


def test_api_transactions_detect_columns_endpoint(import_main_safely):
    client = TestClient(import_main_safely.app)

    called = {}

    def fake_detect(csv_text: str):
        called["csv_text"] = csv_text
        return {
            "ok": True,
            "mapping": {"date": "Transaction Date", "amount": "Amount"},
            "confidence": {"date": 0.99, "amount": 0.99},
            "needs_confirmation": False,
            "strategy": "exact_alias",
        }

    import_main_safely.detect_transaction_csv_mapping = fake_detect

    body = {"csv_text": "Transaction Date,Amount\n2026-05-01,-12.50"}
    response = client.post("/api/transactions/detect-columns", json=body)

    assert response.status_code == 200
    assert called["csv_text"] == body["csv_text"]
    assert response.json()["ok"] is True
    assert response.json()["mapping"]["date"] == "Transaction Date"


def test_api_transactions_import_csv_endpoint_passes_field_mapping(import_main_safely):
    client = TestClient(import_main_safely.app)

    called = {}

    def fake_import(csv_text: str, account_id, field_mapping):
        called["csv_text"] = csv_text
        called["account_id"] = account_id
        called["field_mapping"] = field_mapping
        return {"inserted": 3, "skipped": 1, "errors": [], "total": 4}

    import_main_safely.import_transaction_csv = fake_import

    body = {
        "csv_text": "Transaction Date,Amount\n2026-05-01,-12.50",
        "account_id": 7,
        "field_mapping": {
            "date": "Transaction Date",
            "amount": "Amount",
            "_date_fallback": "Post Date",
        },
    }
    response = client.post("/api/transactions/import-csv", json=body)

    assert response.status_code == 200
    assert called["csv_text"] == body["csv_text"]
    assert called["account_id"] == 7
    assert called["field_mapping"]["date"] == "Transaction Date"
    assert response.json()["inserted"] == 3
