"""Application entrypoint and wiring for finn."""

import atexit
import logging
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.csv_mapper import detect_transaction_csv_mapping
from app.db import init_db
from app.routers.api import router as api_router
from app.routers.pages import router as pages_router
from app.seed import seed_demo
from app.writer import import_transaction_csv, refresh_prices

logger = logging.getLogger(__name__)

__all__ = [
    "_auto_refresh_prices",
    "app",
    "create_app",
    "detect_transaction_csv_mapping",
    "import_transaction_csv",
    "logger",
    "refresh_prices",
]

BASE = Path(__file__).resolve().parent.parent


def _runtime_override(name: str, default):
    runtime_main = sys.modules.get("app.main")
    if runtime_main is None:
        return default
    return getattr(runtime_main, name, default)


def _auto_refresh_prices():
    from app.portfolio import list_portfolios

    refresh_prices_fn = _runtime_override("refresh_prices", refresh_prices)

    for portfolio in list_portfolios():
        path = Path(portfolio["path"])
        if not path.is_absolute():
            path = BASE / path
        if not path.exists():
            continue
        try:
            refresh_prices_fn(db_path=str(path))
            logger.info("Auto price refresh: %s", portfolio["name"])
        except Exception as exc:
            logger.error("Auto price refresh failed for %s: %s", portfolio["name"], exc)


_scheduler = BackgroundScheduler(daemon=True)
_scheduler.add_job(
    _auto_refresh_prices,
    "cron",
    day_of_week="mon-fri",
    hour=16,
    minute=5,
    timezone="America/New_York",
)


def create_app() -> FastAPI:
    app = FastAPI(title="finn", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
    app.state.templates = Jinja2Templates(directory=BASE / "templates")

    @app.middleware("http")
    async def add_static_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/fonts/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    app.include_router(pages_router)
    app.include_router(api_router)

    return app


def _boot_runtime_side_effects() -> None:
    init_db()
    seed_demo()
    _scheduler.start()


_boot_runtime_side_effects()
atexit.register(lambda: _scheduler.shutdown(wait=False))

app = create_app()
