from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.portfolios import (
    create_new_portfolio,
    get_portfolios,
    remove_portfolio,
    rename_existing_portfolio,
    switch_portfolio,
)

router = APIRouter(tags=["portfolios"])


@router.get("/portfolios")
async def api_portfolios():
    return get_portfolios()


class PortfolioSwitchBody(BaseModel):
    name: str


@router.post("/portfolio/switch")
async def api_portfolio_switch(body: PortfolioSwitchBody):
    try:
        return switch_portfolio(body.name)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


class PortfolioNewBody(BaseModel):
    name: str


@router.post("/portfolio/new")
async def api_portfolio_new(body: PortfolioNewBody):
    try:
        return create_new_portfolio(body.name)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


class PortfolioRenameBody(BaseModel):
    name: str


@router.put("/portfolio/{portfolio_name:path}")
async def api_portfolio_rename(portfolio_name: str, body: PortfolioRenameBody):
    try:
        return rename_existing_portfolio(portfolio_name, body.name)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.delete("/portfolio/{portfolio_name:path}")
async def api_portfolio_delete(portfolio_name: str):
    try:
        return remove_portfolio(portfolio_name)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
