"""Portfolio registry — manages portfolios.json at project root."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_DB_DIR = _ROOT / "db"
PORTFOLIOS_FILE = _ROOT / "portfolios.json"


def _ensure_db_dir() -> None:
    _DB_DIR.mkdir(exist_ok=True)


def _load() -> dict:
    _ensure_db_dir()
    if not PORTFOLIOS_FILE.exists():
        cfg = {
            "active": "default",
            "portfolios": [
                {
                    "name": "default",
                    "path": "db/finance.db",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        }
        _save(cfg)
        return cfg
    with open(PORTFOLIOS_FILE) as f:
        return json.load(f)


def _save(cfg: dict) -> None:
    with open(PORTFOLIOS_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def get_active_path() -> Path:
    cfg = _load()
    active = cfg["active"]
    for p in cfg["portfolios"]:
        if p["name"] == active:
            path = Path(p["path"])
            if not path.is_absolute():
                path = _ROOT / path
            return path
    return _DB_DIR / "finance.db"


def list_portfolios() -> list[dict]:
    cfg = _load()
    active = cfg["active"]
    return [{**p, "is_active": p["name"] == active} for p in cfg["portfolios"]]


def set_active(name: str) -> None:
    cfg = _load()
    names = {p["name"] for p in cfg["portfolios"]}
    if name not in names:
        raise ValueError(f"Portfolio {name!r} not found")
    cfg["active"] = name
    _save(cfg)


def rename_portfolio(old_name: str, new_name: str) -> dict:
    display = new_name.strip()
    if not display:
        raise ValueError("Name cannot be empty")
    cfg = _load()
    if any(p["name"] == display for p in cfg["portfolios"] if p["name"] != old_name):
        raise ValueError(f"A portfolio named {display!r} already exists")
    for p in cfg["portfolios"]:
        if p["name"] == old_name:
            p["name"] = display
            if cfg["active"] == old_name:
                cfg["active"] = display
            _save(cfg)
            return p
    raise ValueError(f"Portfolio {old_name!r} not found")


def delete_portfolio(name: str) -> None:
    cfg = _load()
    if cfg["active"] == name:
        raise ValueError("Cannot delete the active portfolio. Switch to another first.")
    if len(cfg["portfolios"]) <= 1:
        raise ValueError("Cannot delete the last portfolio.")
    entry = next((p for p in cfg["portfolios"] if p["name"] == name), None)
    if not entry:
        raise ValueError(f"Portfolio {name!r} not found")
    cfg["portfolios"] = [p for p in cfg["portfolios"] if p["name"] != name]
    _save(cfg)
    db_path = Path(entry["path"])
    if not db_path.is_absolute():
        db_path = _ROOT / db_path
    try:
        db_path.unlink(missing_ok=True)
        for ext in ("-shm", "-wal"):
            (db_path.parent / (db_path.name + ext)).unlink(missing_ok=True)
    except OSError:
        pass


def create_portfolio(name: str) -> dict:
    """Add a new portfolio to the registry, set it as active, and return the entry."""
    display_name = name.strip()
    if not display_name:
        raise ValueError("Portfolio name cannot be empty")

    cfg = _load()
    if any(p["name"] == display_name for p in cfg["portfolios"]):
        raise ValueError(f"A portfolio named {display_name!r} already exists")

    _ensure_db_dir()
    safe = re.sub(r"[^a-z0-9_-]+", "_", display_name.lower()).strip("_") or "portfolio"
    db_name = f"db/{safe}.db"
    n = 1
    while any(p["path"] == db_name for p in cfg["portfolios"]):
        db_name = f"db/{safe}_{n}.db"
        n += 1

    entry = {
        "name": display_name,
        "path": db_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    cfg["portfolios"].append(entry)
    cfg["active"] = display_name
    _save(cfg)
    return entry
