from app.db import init_db
from app.portfolio import _load, create_portfolio, delete_portfolio, list_portfolios, rename_portfolio, set_active
from app.seed import seed_demo


def get_portfolios() -> dict:
    cfg = _load()
    return {"active": cfg["active"], "portfolios": list_portfolios()}


def switch_portfolio(name: str) -> dict:
    set_active(name)
    init_db()
    return {"ok": True, "active": name}


def create_new_portfolio(name: str) -> dict:
    entry = create_portfolio(name)
    init_db()
    seed_demo()
    return {"ok": True, **entry}


def rename_existing_portfolio(current_name: str, new_name: str) -> dict:
    entry = rename_portfolio(current_name, new_name)
    return {"ok": True, **entry}


def remove_portfolio(name: str) -> dict:
    delete_portfolio(name)
    return {"ok": True}


__all__ = [
    "create_new_portfolio",
    "get_portfolios",
    "remove_portfolio",
    "rename_existing_portfolio",
    "switch_portfolio",
]
