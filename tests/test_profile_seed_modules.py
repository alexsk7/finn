from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.db import get_conn


def test_profile_defaults_and_invalid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.profile as profile

    profile_file = tmp_path / "profile.json"
    monkeypatch.setattr(profile, "_PROFILE_FILE", profile_file)

    assert profile._load() == {"user_name": "", "currency_symbol": "$"}

    profile_file.write_text("{bad json", encoding="utf-8")
    assert profile._load() == {"user_name": "", "currency_symbol": "$"}


def test_save_profile_strips_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.profile as profile

    profile_file = tmp_path / "profile.json"
    monkeypatch.setattr(profile, "_PROFILE_FILE", profile_file)

    profile.save_profile("  Alex  ", "")
    loaded = json.loads(profile_file.read_text())

    assert loaded == {"user_name": "Alex", "currency_symbol": "$"}


def test_migrate_profile_from_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.portfolio as portfolio
    import app.profile as profile

    profile_file = tmp_path / "profile.json"
    db_path = tmp_path / "active.db"

    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE app_flags (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO app_flags(key, value) VALUES ('user_name', 'Jordan')")
        conn.execute("INSERT INTO app_flags(key, value) VALUES ('currency_symbol', '€')")

    monkeypatch.setattr(profile, "_PROFILE_FILE", profile_file)
    monkeypatch.setattr(portfolio, "get_active_path", lambda: db_path)

    got = profile.get_profile()

    assert got == {"user_name": "Jordan", "currency_symbol": "€"}
    assert profile_file.exists()


def test_migrate_profile_no_db_is_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import app.portfolio as portfolio
    import app.profile as profile

    profile_file = tmp_path / "profile.json"
    missing_db = tmp_path / "missing.db"

    monkeypatch.setattr(profile, "_PROFILE_FILE", profile_file)
    monkeypatch.setattr(portfolio, "get_active_path", lambda: missing_db)

    assert profile.get_profile() == {"user_name": "", "currency_symbol": "$"}


def test_seed_demo_inserts_once(init_schema: Path, monkeypatch: pytest.MonkeyPatch):
    import app.seed as seed

    @contextmanager
    def test_conn():
        with get_conn(db_path=str(init_schema)) as conn:
            yield conn

    monkeypatch.setattr(seed, "get_conn", test_conn)

    seed.seed_demo()
    with get_conn(db_path=str(init_schema)) as conn:
        first_count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        flag = conn.execute("SELECT value FROM app_flags WHERE key='demo_seeded'").fetchone()[0]

    seed.seed_demo()
    with get_conn(db_path=str(init_schema)) as conn:
        second_count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]

    assert first_count > 0
    assert second_count == first_count
    assert flag == "1"


def test_seed_demo_marks_existing_db_without_full_seed(init_schema: Path, monkeypatch: pytest.MonkeyPatch):
    import app.seed as seed

    with get_conn(db_path=str(init_schema)) as conn:
        conn.execute("INSERT INTO accounts(name, institution, type) VALUES ('Existing', 'Bank', 'checking')")

    @contextmanager
    def test_conn():
        with get_conn(db_path=str(init_schema)) as conn:
            yield conn

    monkeypatch.setattr(seed, "get_conn", test_conn)

    seed.seed_demo()

    with get_conn(db_path=str(init_schema)) as conn:
        account_count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        flag = conn.execute("SELECT value FROM app_flags WHERE key='demo_seeded'").fetchone()[0]

    assert account_count == 1
    assert flag == "1"
