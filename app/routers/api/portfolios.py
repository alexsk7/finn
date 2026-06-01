from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db import init_db
from app.portfolio import _load, create_portfolio, delete_portfolio, list_portfolios, rename_portfolio, set_active
from app.schemas.portfolios import PortfolioNewBody, PortfolioRenameBody, PortfolioSwitchBody
from app.seed import seed_demo

router = APIRouter(tags=["portfolios"])


def get_portfolios() -> dict:
    cfg = _load()
    return {"active": cfg["active"], "portfolios": list_portfolios()}


def _bad_request(error: ValueError):
    return JSONResponse(status_code=400, content={"error": str(error)})


@router.get("/portfolios")
async def api_portfolios():
    return get_portfolios()


@router.post("/portfolio/switch")
async def api_portfolio_switch(body: PortfolioSwitchBody):
    try:
        set_active(body.name)
        init_db()
        return {"ok": True, "active": body.name}
    except ValueError as e:
        return _bad_request(e)


@router.post("/portfolio/new")
async def api_portfolio_new(body: PortfolioNewBody):
    try:
        entry = create_portfolio(body.name)
        init_db()
        seed_demo()
        return {"ok": True, **entry}
    except ValueError as e:
        return _bad_request(e)


@router.put("/portfolio/{portfolio_name:path}")
async def api_portfolio_rename(portfolio_name: str, body: PortfolioRenameBody):
    try:
        entry = rename_portfolio(portfolio_name, body.name)
        return {"ok": True, **entry}
    except ValueError as e:
        return _bad_request(e)


@router.delete("/portfolio/{portfolio_name:path}")
async def api_portfolio_delete(portfolio_name: str):
    try:
        delete_portfolio(portfolio_name)
        return {"ok": True}
    except ValueError as e:
        return _bad_request(e)
