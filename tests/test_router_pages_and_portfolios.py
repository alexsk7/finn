from fastapi.testclient import TestClient


def test_pages_routes_render_html(import_main_safely):
    client = TestClient(import_main_safely.app)

    for path in [
        "/",
        "/landing",
        "/investments",
        "/accounts",
        "/accounts/1",
        "/real-estate",
        "/tax",
        "/rebalance",
        "/journal",
        "/budget",
        "/data",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


def test_portfolios_router_success_paths(import_main_safely, monkeypatch):
    client = TestClient(import_main_safely.app)

    monkeypatch.setattr("app.routers.api.portfolios.get_portfolios", lambda: {"active": "default", "portfolios": []})
    monkeypatch.setattr("app.routers.api.portfolios.switch_portfolio", lambda name: {"ok": True, "active": name})
    monkeypatch.setattr("app.routers.api.portfolios.create_new_portfolio", lambda name: {"ok": True, "name": name})
    monkeypatch.setattr(
        "app.routers.api.portfolios.rename_existing_portfolio",
        lambda old_name, new_name: {"ok": True, "name": new_name, "old": old_name},
    )
    monkeypatch.setattr("app.routers.api.portfolios.remove_portfolio", lambda name: {"ok": True, "removed": name})

    assert client.get("/api/portfolios").status_code == 200
    assert client.post("/api/portfolio/switch", json={"name": "alt"}).json()["active"] == "alt"
    assert client.post("/api/portfolio/new", json={"name": "newp"}).json()["ok"] is True
    assert client.put("/api/portfolio/default", json={"name": "renamed"}).json()["name"] == "renamed"
    assert client.delete("/api/portfolio/to-delete").json()["removed"] == "to-delete"


def test_portfolios_router_error_paths(import_main_safely, monkeypatch):
    client = TestClient(import_main_safely.app)

    def boom(*args, **kwargs):
        raise ValueError("bad request")

    monkeypatch.setattr("app.routers.api.portfolios.switch_portfolio", boom)
    monkeypatch.setattr("app.routers.api.portfolios.create_new_portfolio", boom)
    monkeypatch.setattr("app.routers.api.portfolios.rename_existing_portfolio", boom)
    monkeypatch.setattr("app.routers.api.portfolios.remove_portfolio", boom)

    assert client.post("/api/portfolio/switch", json={"name": "x"}).status_code == 400
    assert client.post("/api/portfolio/new", json={"name": "x"}).status_code == 400
    assert client.put("/api/portfolio/x", json={"name": "y"}).status_code == 400
    assert client.delete("/api/portfolio/x").status_code == 400
