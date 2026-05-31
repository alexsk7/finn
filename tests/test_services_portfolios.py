import pytest

from app.services import portfolios as svc


def test_get_portfolios(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.services.portfolios._load", lambda: {"active": "default"})
    monkeypatch.setattr("app.services.portfolios.list_portfolios", lambda: [{"name": "default", "is_active": True}])

    got = svc.get_portfolios()
    assert got["active"] == "default"
    assert got["portfolios"][0]["name"] == "default"


def test_switch_portfolio(monkeypatch: pytest.MonkeyPatch):
    called_set: list[str] = []
    init_calls = 0

    def fake_set_active(name: str):
        called_set.append(name)

    def fake_init_db():
        nonlocal init_calls
        init_calls += 1

    monkeypatch.setattr("app.services.portfolios.set_active", fake_set_active)
    monkeypatch.setattr("app.services.portfolios.init_db", fake_init_db)

    got = svc.switch_portfolio("alt")
    assert got == {"ok": True, "active": "alt"}
    assert called_set == ["alt"]
    assert init_calls == 1


def test_create_new_portfolio(monkeypatch: pytest.MonkeyPatch):
    calls = {"init": 0, "seed": 0}

    monkeypatch.setattr("app.services.portfolios.create_portfolio", lambda name: {"name": name, "path": "db/x.db"})
    monkeypatch.setattr("app.services.portfolios.init_db", lambda: calls.__setitem__("init", calls["init"] + 1))
    monkeypatch.setattr("app.services.portfolios.seed_demo", lambda: calls.__setitem__("seed", calls["seed"] + 1))

    got = svc.create_new_portfolio("new")
    assert got["ok"] is True
    assert got["name"] == "new"
    assert calls == {"init": 1, "seed": 1}


def test_rename_and_remove(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.services.portfolios.rename_portfolio", lambda old, new: {"name": new, "path": "db/new.db"})

    removed = {"name": None}
    monkeypatch.setattr("app.services.portfolios.delete_portfolio", lambda name: removed.__setitem__("name", name))

    renamed = svc.rename_existing_portfolio("old", "new")
    deleted = svc.remove_portfolio("gone")

    assert renamed == {"ok": True, "name": "new", "path": "db/new.db"}
    assert deleted == {"ok": True}
    assert removed["name"] == "gone"
