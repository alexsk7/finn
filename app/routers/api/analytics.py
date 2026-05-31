from fastapi import APIRouter

from app.services.reads import (
    get_allocation,
    get_cashflow_by_category,
    get_dashboard_summary,
    get_rebalance,
    get_tax_summary,
    get_ticker_data,
)

router = APIRouter(tags=["analytics"])


@router.get("/dashboard")
async def api_dashboard():
    return get_dashboard_summary()


@router.get("/allocation")
async def api_allocation():
    return get_allocation()


@router.get("/tax")
async def api_tax():
    return get_tax_summary()


@router.get("/rebalance")
async def api_rebalance(new_cash: float = 0.0):
    return get_rebalance(new_cash)


@router.get("/cashflow")
async def api_cashflow():
    return get_cashflow_by_category()


@router.get("/ticker")
async def api_ticker():
    return get_ticker_data()
