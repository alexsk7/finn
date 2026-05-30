from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest

from app.db import get_conn, init_db


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Create an isolated SQLite path for a single test."""
    return tmp_path / "test.db"


@pytest.fixture
def init_schema(tmp_db_path: Path) -> Path:
    """Initialize schema only (no demo seed) for the temp DB."""
    init_db(db_path=str(tmp_db_path))
    return tmp_db_path


@pytest.fixture
def monkeypatch_active_db(monkeypatch: pytest.MonkeyPatch, init_schema: Path) -> Path:
    """Route default get_conn() calls to the temp DB via portfolio active path."""
    monkeypatch.setattr("app.portfolio.get_active_path", lambda: init_schema)
    return init_schema


@pytest.fixture
def db_conn(monkeypatch_active_db: Path):
    """Yield a live connection to the isolated DB configured as active."""
    with get_conn() as conn:
        yield conn


@pytest.fixture
def minimal_seed_data(db_conn) -> dict[str, Any]:
    """Insert a compact, deterministic baseline dataset for read/write tests."""
    db_conn.executescript("""
        INSERT INTO accounts (id, name, institution, type, opening_balance) VALUES
            (1, 'Test Checking', 'Chase', 'checking', 5000),
            (2, 'Test Brokerage', 'Fidelity', 'brokerage', 0),
            (3, 'Test Mortgage', 'Rocket', 'loan', 300000);

        INSERT INTO holdings (account_id, symbol, name, asset_class, shares, cost_basis, updated_at, is_manual) VALUES
            (2, 'VTI', 'Vanguard Total Stock Market ETF', 'us_equity', 10, 220, '2026-05-01', 0),
            (2, 'VXUS', 'Vanguard Total International', 'intl_equity', 5, 55, '2026-05-01', 0);

        INSERT INTO prices (symbol, price, prev_close, recorded_at) VALUES
            ('VTI', 270.00, 268.00, '2026-05-01 10:00:00'),
            ('VXUS', 62.00, 61.50, '2026-05-01 10:00:00');

        INSERT INTO transactions (txn_date, account_id, amount, direction, category, payee, description, recurring) VALUES
            ('2026-05-01', 1, 3000.00, 'income',  'Salary',   'Employer', 'Paycheck', 1),
            ('2026-05-02', 1, 1200.00, 'expense', 'Housing',  'Mortgage', 'Mortgage payment', 1),
            ('2026-05-03', 3, 1200.00, 'expense', 'Housing',  'Mortgage', 'Mortgage payment', 1);

        INSERT INTO allocation_targets (asset_class, target_pct) VALUES
            ('us_equity', 60),
            ('intl_equity', 20),
            ('bond', 20);

        INSERT INTO real_estate (id, name, estimated_value, mortgage_balance, purchase_price, purchase_date, updated_at, account_id) VALUES
            (1, 'Primary Residence', 500000, 300000, 420000, '2020-06-15', '2026-05-01', 3);

        INSERT INTO snapshots (snapshot_date, net_worth, liquid_cash, invested_total, home_equity, debt_total, other_assets, notes) VALUES
            ('2026-04-01', 200000, 5000, 3000, 200000, 300000, 0, 'baseline');
    """)

    return {
        "accounts": {
            "checking": 1,
            "brokerage": 2,
            "mortgage": 3,
        },
        "property_id": 1,
    }


@pytest.fixture
def import_main_safely(monkeypatch: pytest.MonkeyPatch):
    """Import main.py with startup side effects disabled for API/scheduler tests."""

    class _DummyScheduler:
        def __init__(self, *args, **kwargs):
            self.jobs: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

        def add_job(self, *args, **kwargs):
            self.jobs.append((args, kwargs))

        def start(self) -> None:
            return None

        def shutdown(self, wait: bool = False) -> None:  # pragma: no cover - trivial no-op
            return None

    monkeypatch.setattr("app.db.init_db", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.seed.seed_demo", lambda *args, **kwargs: None)
    monkeypatch.setattr("apscheduler.schedulers.background.BackgroundScheduler", _DummyScheduler)

    if "main" in sys.modules:
        del sys.modules["main"]

    return importlib.import_module("main")
