"""App-level user profile — stored in profile.json at the project root.

Profile is installation-scoped, not portfolio-scoped. Switching portfolios
or sharing a DB file does not change whose name and currency symbol appear.
"""

import json
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_PROFILE_FILE = _ROOT / "profile.json"

_DEFAULTS = {"user_name": "", "currency_symbol": "$"}


def _load() -> dict:
    if _PROFILE_FILE.exists():
        try:
            data = json.loads(_PROFILE_FILE.read_text())
            return {**_DEFAULTS, **data}
        except Exception:
            pass
    return dict(_DEFAULTS)


def _save(profile: dict) -> None:
    _PROFILE_FILE.write_text(json.dumps(profile, indent=2))


def _migrate_from_db() -> None:
    """One-shot: if profile.json is absent, seed it from the active portfolio's app_flags."""
    if _PROFILE_FILE.exists():
        return
    try:
        import sqlite3

        from .portfolio import get_active_path

        db_path = get_active_path()
        if not db_path.exists():
            return
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT key, value FROM app_flags WHERE key IN ('user_name', 'currency_symbol')"
            ).fetchall()
        m = {r["key"]: r["value"] for r in rows}
        if m.get("user_name") or m.get("currency_symbol"):
            _save(
                {
                    "user_name": m.get("user_name", ""),
                    "currency_symbol": m.get("currency_symbol", "$"),
                }
            )
    except Exception:
        pass


def get_profile() -> dict:
    _migrate_from_db()
    return _load()


def save_profile(user_name: str, currency_symbol: str) -> None:
    _save(
        {
            "user_name": user_name.strip(),
            "currency_symbol": currency_symbol.strip() or "$",
        }
    )
