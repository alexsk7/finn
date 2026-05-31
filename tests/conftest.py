from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import pytest
from freezegun import freeze_time

from app.db import get_conn, init_db


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Create an isolated SQLite path for a single test."""
    return tmp_path / "test.db"


@pytest.fixture
def test_db_lifecycle(tmp_db_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Initialize a fresh DB and explicitly tear it down after each test."""
    init_db(db_path=str(tmp_db_path))
    monkeypatch.setattr("app.portfolio.get_active_path", lambda: tmp_db_path)

    try:
        yield tmp_db_path
    finally:
        with get_conn(db_path=str(tmp_db_path)) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        for suffix in ("", "-wal", "-shm"):
            db_file = tmp_db_path.parent / f"{tmp_db_path.name}{suffix}"
            db_file.unlink(missing_ok=True)
            assert not db_file.exists(), f"Expected test DB artifact to be removed: {db_file}"


@pytest.fixture
def init_schema(test_db_lifecycle: Path) -> Path:
    """Backward-compatible alias for schema-initialized isolated DB."""
    return test_db_lifecycle


@pytest.fixture
def monkeypatch_active_db(test_db_lifecycle: Path) -> Path:
    """Backward-compatible alias for active DB monkeypatch fixture."""
    return test_db_lifecycle


@pytest.fixture
def db_conn(test_db_lifecycle: Path):
    """Yield a live connection to the isolated DB configured as active."""
    with get_conn(db_path=str(test_db_lifecycle)) as conn:
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
    """Import app.main with startup side effects disabled for API/scheduler tests."""

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

    if "app.main" in sys.modules:
        del sys.modules["app.main"]

    return importlib.import_module("app.main")


@pytest.fixture
def frozen_now():
    """Return a helper that freezes application time for deterministic tests."""

    def _freeze(when: str = "2026-05-30 12:34:56"):
        return freeze_time(when, tz_offset=0)

    return _freeze


@pytest.fixture
def mock_yfinance_ticker(monkeypatch: pytest.MonkeyPatch):
    """Patch yfinance.Ticker with configurable per-symbol responses."""

    class _FakeSeries:
        def __init__(self, values: list[float]):
            self._values = values

        @property
        def iloc(self):
            return self

        def __getitem__(self, idx: int) -> float:
            return self._values[idx]

    class _FakeHistory:
        def __init__(self, closes: list[float]):
            self._closes = closes

        @property
        def empty(self) -> bool:
            return len(self._closes) == 0

        def __len__(self) -> int:
            return len(self._closes)

        def __getitem__(self, key: str) -> _FakeSeries:
            if key != "Close":
                raise KeyError(key)
            return _FakeSeries(self._closes)

    class _FastInfo:
        def __init__(self, last_price: float, previous_close: float | None = None):
            self.last_price = last_price
            self.previous_close = previous_close

    class _FakeTicker:
        def __init__(self, symbol: str, cfg: dict[str, Any]):
            self.symbol = symbol
            self._cfg = cfg

        @property
        def fast_info(self):
            if "fast_error" in self._cfg:
                raise self._cfg["fast_error"]
            last = self._cfg.get("last_price", 100.0)
            prev = self._cfg.get("previous_close", 99.0)
            return _FastInfo(last, prev)

        def history(self, period: str = "2d") -> _FakeHistory:
            if "history_error" in self._cfg:
                raise self._cfg["history_error"]
            closes = self._cfg.get("history_closes", [98.0, 100.0])
            return _FakeHistory(closes)

    class _Controller:
        def __init__(self):
            self._per_symbol: dict[str, dict[str, Any]] = {}
            self.called_symbols: list[str] = []

        def set_fast(self, symbol: str, *, last_price: float, previous_close: float | None = None) -> None:
            cfg = self._per_symbol.setdefault(symbol, {})
            cfg["last_price"] = last_price
            cfg["previous_close"] = previous_close
            cfg.pop("fast_error", None)

        def set_fast_exception(self, symbol: str, exc: Exception | None = None) -> None:
            cfg = self._per_symbol.setdefault(symbol, {})
            cfg["fast_error"] = exc or RuntimeError("fast_info unavailable")

        def set_history(self, symbol: str, closes: list[float]) -> None:
            cfg = self._per_symbol.setdefault(symbol, {})
            cfg["history_closes"] = closes
            cfg.pop("history_error", None)

        def set_history_exception(self, symbol: str, exc: Exception | None = None) -> None:
            cfg = self._per_symbol.setdefault(symbol, {})
            cfg["history_error"] = exc or RuntimeError("history unavailable")

        def set_constructor_exception(self, symbol: str, exc: Exception | None = None) -> None:
            cfg = self._per_symbol.setdefault(symbol, {})
            cfg["ctor_error"] = exc or RuntimeError("ticker construction failed")

        def _ticker(self, symbol: str) -> _FakeTicker:
            self.called_symbols.append(symbol)
            cfg = self._per_symbol.get(symbol, {})
            if "ctor_error" in cfg:
                raise cfg["ctor_error"]
            return _FakeTicker(symbol, cfg)

    controller = _Controller()

    class _FakeYFModule:
        Ticker = staticmethod(controller._ticker)

    monkeypatch.setitem(sys.modules, "yfinance", _FakeYFModule())
    return controller
