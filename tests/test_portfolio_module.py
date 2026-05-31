from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def isolated_portfolio_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.portfolio as portfolio

    root = tmp_path
    db_dir = root / "db"
    portfolios_file = root / "portfolios.json"

    monkeypatch.setattr(portfolio, "_ROOT", root)
    monkeypatch.setattr(portfolio, "_DB_DIR", db_dir)
    monkeypatch.setattr(portfolio, "PORTFOLIOS_FILE", portfolios_file)

    return portfolio, root, db_dir, portfolios_file


def test_load_creates_default_registry(isolated_portfolio_registry):
    portfolio, _, db_dir, portfolios_file = isolated_portfolio_registry

    cfg = portfolio._load()

    assert cfg["active"] == "default"
    assert cfg["portfolios"][0]["path"] == "db/finance.db"
    assert db_dir.exists()
    assert portfolios_file.exists()


def test_get_active_path_and_fallback(isolated_portfolio_registry):
    portfolio, root, db_dir, _ = isolated_portfolio_registry

    portfolio._save({
        "active": "custom",
        "portfolios": [{"name": "custom", "path": "db/custom.db", "created_at": "now"}],
    })

    assert portfolio.get_active_path() == root / "db" / "custom.db"

    portfolio._save({
        "active": "missing",
        "portfolios": [{"name": "custom", "path": "db/custom.db", "created_at": "now"}],
    })
    assert portfolio.get_active_path() == db_dir / "finance.db"


def test_set_active_and_list_portfolios(isolated_portfolio_registry):
    portfolio, _, _, _ = isolated_portfolio_registry

    portfolio._save({
        "active": "default",
        "portfolios": [
            {"name": "default", "path": "db/finance.db", "created_at": "now"},
            {"name": "retire", "path": "db/retire.db", "created_at": "now"},
        ],
    })

    portfolio.set_active("retire")
    listed = portfolio.list_portfolios()

    assert any(p["name"] == "retire" and p["is_active"] for p in listed)

    with pytest.raises(ValueError, match="not found"):
        portfolio.set_active("ghost")


def test_rename_portfolio_validations_and_active_update(isolated_portfolio_registry):
    portfolio, _, _, _ = isolated_portfolio_registry

    portfolio._save({
        "active": "default",
        "portfolios": [
            {"name": "default", "path": "db/finance.db", "created_at": "now"},
            {"name": "retire", "path": "db/retire.db", "created_at": "now"},
        ],
    })

    updated = portfolio.rename_portfolio("default", "  primary  ")
    cfg = portfolio._load()

    assert updated["name"] == "primary"
    assert cfg["active"] == "primary"

    with pytest.raises(ValueError, match="already exists"):
        portfolio.rename_portfolio("primary", "retire")

    with pytest.raises(ValueError, match="cannot be empty"):
        portfolio.rename_portfolio("primary", "   ")

    with pytest.raises(ValueError, match="not found"):
        portfolio.rename_portfolio("ghost", "new")


def test_create_portfolio_sanitizes_and_unique_db_paths(isolated_portfolio_registry):
    portfolio, _, _, _ = isolated_portfolio_registry

    portfolio._load()
    first = portfolio.create_portfolio("My Long Name!!")
    second = portfolio.create_portfolio("my long name")

    assert first["path"] == "db/my_long_name.db"
    assert second["path"] == "db/my_long_name_1.db"

    with pytest.raises(ValueError, match="cannot be empty"):
        portfolio.create_portfolio(" ")

    with pytest.raises(ValueError, match="already exists"):
        portfolio.create_portfolio("My Long Name!!")


def test_delete_portfolio_validations_and_file_cleanup(isolated_portfolio_registry):
    portfolio, root, _, _ = isolated_portfolio_registry

    portfolio._save({
        "active": "default",
        "portfolios": [
            {"name": "default", "path": "db/finance.db", "created_at": "now"},
            {"name": "retire", "path": "db/retire.db", "created_at": "now"},
        ],
    })

    db_file = root / "db" / "retire.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    db_file.write_text("", encoding="utf-8")
    (root / "db" / "retire.db-wal").write_text("", encoding="utf-8")
    (root / "db" / "retire.db-shm").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="active portfolio"):
        portfolio.delete_portfolio("default")

    with pytest.raises(ValueError, match="not found"):
        portfolio.delete_portfolio("ghost")

    portfolio.delete_portfolio("retire")
    cfg = json.loads((root / "portfolios.json").read_text())

    assert len(cfg["portfolios"]) == 1
    assert not db_file.exists()
    assert not (root / "db" / "retire.db-wal").exists()
    assert not (root / "db" / "retire.db-shm").exists()

    portfolio._save({
        "active": "other",
        "portfolios": [{"name": "default", "path": "db/finance.db", "created_at": "now"}],
    })

    with pytest.raises(ValueError, match="last portfolio"):
        portfolio.delete_portfolio("default")
