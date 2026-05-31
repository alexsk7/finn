from fastapi.testclient import TestClient


def test_budget_router_success_and_error_paths(import_main_safely, monkeypatch):
    client = TestClient(import_main_safely.app)

    monkeypatch.setattr("app.routers.api.budget.get_budget_month", lambda month=None: {"month": month or "2026-05"})
    monkeypatch.setattr("app.routers.api.budget.get_budget_categories_full", lambda: [{"id": 1, "name": "Housing"}])
    monkeypatch.setattr("app.routers.api.budget.add_budget_category", lambda *args: {"ok": True})
    monkeypatch.setattr("app.routers.api.budget.update_budget_category", lambda *args: {"ok": True})
    monkeypatch.setattr("app.routers.api.budget.delete_budget_category", lambda *args: None)
    monkeypatch.setattr("app.routers.api.budget.save_budget_month", lambda *args: {"ok": True})
    monkeypatch.setattr("app.routers.api.budget.copy_budget_month", lambda *args: {"ok": True})

    assert client.get("/api/budget?month=2026-05").status_code == 200
    assert client.get("/api/budget-categories").status_code == 200
    assert (
        client.post(
            "/api/budget-categories", json={"name": "Food", "monthly_target": 500, "direction": "expense"}
        ).status_code
        == 200
    )
    assert client.put("/api/budget-categories/1", json={"name": "Food", "monthly_target": 600}).status_code == 200
    assert client.delete("/api/budget-categories/1").json()["ok"] is True

    save_body = {"items": [{"category_id": 1, "planned_amount": 100}], "notes": "ok"}
    assert client.put("/api/budget/months/2026-05", json=save_body).status_code == 200
    assert (
        client.post("/api/budget/months/2026-06/copy", json={"source_month": "2026-05", "overwrite": False}).status_code
        == 200
    )

    def bad_budget(*args, **kwargs):
        raise ValueError("bad month")

    monkeypatch.setattr("app.routers.api.budget.get_budget_month", bad_budget)
    assert client.get("/api/budget?month=bad").status_code == 400

    monkeypatch.setattr("app.routers.api.budget.save_budget_month", bad_budget)
    assert client.put("/api/budget/months/2026-05", json=save_body).status_code == 400

    monkeypatch.setattr(
        "app.routers.api.budget.copy_budget_month",
        lambda *args: (_ for _ in ()).throw(ValueError("already has a plan")),
    )
    assert (
        client.post("/api/budget/months/2026-06/copy", json={"source_month": "2026-05", "overwrite": False}).status_code
        == 409
    )

    monkeypatch.setattr("app.routers.api.budget.copy_budget_month", bad_budget)
    assert (
        client.post("/api/budget/months/2026-06/copy", json={"source_month": "2026-05", "overwrite": False}).status_code
        == 400
    )


def test_investments_router_routes_and_validation(import_main_safely, monkeypatch):
    client = TestClient(import_main_safely.app)

    monkeypatch.setattr(
        "app.routers.api.investments.get_allocation_targets", lambda: [{"asset_class": "us_equity", "target_pct": 60}]
    )
    monkeypatch.setattr("app.routers.api.investments.upsert_allocation_target", lambda *args: {"ok": True})
    monkeypatch.setattr("app.routers.api.investments.get_all_holdings_raw", lambda: [{"id": 1, "symbol": "VTI"}])
    monkeypatch.setattr("app.routers.api.investments.add_holding", lambda *args: {"id": 1})
    monkeypatch.setattr("app.routers.api.investments.update_holding", lambda *args: {"ok": True})
    monkeypatch.setattr("app.routers.api.investments.delete_holding", lambda *args: None)
    monkeypatch.setattr("app.routers.api.investments.import_holdings_csv", lambda *args: {"inserted": 2})
    monkeypatch.setattr("app.routers.api.investments.update_price", lambda *args: None)
    monkeypatch.setattr("app.routers.api.investments.save_snapshot", lambda *args: {"ok": True})
    monkeypatch.setattr("app.routers.api.investments.import_snapshot_csv", lambda *args: {"inserted": 1})

    def fake_refresh_prices(**kwargs):
        return {"updated": [], "failed": []}

    import_main_safely.refresh_prices = fake_refresh_prices

    assert client.get("/api/allocation-targets").status_code == 200
    assert (
        client.post("/api/allocation-targets", json={"asset_class": "us_equity", "target_pct": 60}).status_code == 200
    )
    assert client.get("/api/holdings").status_code == 200

    invalid_manual = {
        "account_id": 1,
        "symbol": "VTI",
        "asset_class": "us_equity",
        "shares": 1,
        "cost_basis": 1,
        "name": "ETF",
        "is_manual": True,
    }
    assert client.post("/api/holdings", json=invalid_manual).status_code == 400

    invalid_non_manual = dict(invalid_manual)
    invalid_non_manual["is_manual"] = False
    invalid_non_manual["symbol"] = "M:CUSTOM"
    assert client.post("/api/holdings", json=invalid_non_manual).status_code == 400

    valid_manual = dict(invalid_manual)
    valid_manual["symbol"] = "M:CUSTOM"
    assert client.post("/api/holdings", json=valid_manual).status_code == 200
    assert client.put("/api/holdings/1", json=valid_manual).status_code == 200

    assert client.delete("/api/holdings/1").json()["ok"] is True
    assert (
        client.post("/api/holdings/import-csv", json={"csv_text": "symbol,shares\nVTI,1", "account_id": 1}).status_code
        == 200
    )

    assert client.post("/api/prices/refresh").status_code == 200
    assert client.post("/api/prices/manual", json={"symbol": "vti", "price": 123.45}).json()["symbol"] == "VTI"

    assert (
        client.post(
            "/api/snapshot",
            json={
                "account_balances": [{"account_id": 1, "balance": 1000}],
                "snapshot_date": "2026-05-01",
                "notes": "ok",
            },
        ).status_code
        == 200
    )
    assert (
        client.post("/api/snapshots/import-csv", json={"csv_text": "date,net_worth\n2026-05-01,1000"}).status_code
        == 200
    )


def test_system_reset_router(import_main_safely, monkeypatch):
    client = TestClient(import_main_safely.app)

    calls = {"n": 0}
    monkeypatch.setattr("app.routers.api.system.reset_all_data", lambda: calls.__setitem__("n", calls["n"] + 1))

    assert client.post("/api/reset", json={"confirm": "NOPE"}).status_code == 400

    ok = client.post("/api/reset", json={"confirm": "RESET"})
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
    assert calls["n"] == 1
