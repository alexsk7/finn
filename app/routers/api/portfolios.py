from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(tags=["portfolios"])


@router.get("/portfolios")
async def api_portfolios():
    from app.portfolio import _load, list_portfolios

    cfg = _load()
    return {"active": cfg["active"], "portfolios": list_portfolios()}


class PortfolioSwitchBody(BaseModel):
    name: str


@router.post("/portfolio/switch")
async def api_portfolio_switch(body: PortfolioSwitchBody):
    from app.db import init_db
    from app.portfolio import set_active

    try:
        set_active(body.name)
        init_db()
        return {"ok": True, "active": body.name}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


class PortfolioNewBody(BaseModel):
    name: str


@router.post("/portfolio/new")
async def api_portfolio_new(body: PortfolioNewBody):
    from app.db import init_db
    from app.portfolio import create_portfolio
    from app.seed import seed_demo

    try:
        entry = create_portfolio(body.name)
        init_db()
        seed_demo()
        return {"ok": True, **entry}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


class PortfolioRenameBody(BaseModel):
    name: str


@router.put("/portfolio/{portfolio_name:path}")
async def api_portfolio_rename(portfolio_name: str, body: PortfolioRenameBody):
    from app.portfolio import rename_portfolio

    try:
        entry = rename_portfolio(portfolio_name, body.name)
        return {"ok": True, **entry}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.delete("/portfolio/{portfolio_name:path}")
async def api_portfolio_delete(portfolio_name: str):
    from app.portfolio import delete_portfolio

    try:
        delete_portfolio(portfolio_name)
        return {"ok": True}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
