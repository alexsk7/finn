from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.real_estate import (
    add_real_estate,
    delete_real_estate,
    get_amortization,
    get_real_estate,
    link_real_estate_account,
    save_mortgage_config,
    update_real_estate,
    upsert_property_cost,
)

router = APIRouter(tags=["real-estate"])


@router.get("/real-estate")
async def api_real_estate():
    return get_real_estate()


class RealEstateUpdate(BaseModel):
    property_id: int
    estimated_value: float
    mortgage_balance: float


@router.post("/real-estate/update")
async def api_real_estate_update(body: RealEstateUpdate):
    return update_real_estate(body.property_id, body.estimated_value, body.mortgage_balance)


class RealEstateAdd(BaseModel):
    name: str
    estimated_value: float
    mortgage_balance: float = 0
    address: Optional[str] = None
    purchase_price: float = 0
    purchase_date: Optional[str] = None
    account_id: Optional[int] = None


@router.post("/real-estate")
async def api_real_estate_add(body: RealEstateAdd):
    return add_real_estate(
        body.name,
        body.estimated_value,
        body.mortgage_balance,
        body.address,
        body.purchase_price,
        body.purchase_date,
        body.account_id,
    )


class RealEstateLinkBody(BaseModel):
    account_id: Optional[int] = None


@router.post("/real-estate/{property_id}/link-account")
async def api_real_estate_link(property_id: int, body: RealEstateLinkBody):
    return link_real_estate_account(property_id, body.account_id)


@router.delete("/real-estate/{property_id}")
async def api_real_estate_delete(property_id: int):
    return delete_real_estate(property_id)


@router.get("/real-estate/{property_id}/amortization")
async def api_amortization(property_id: int):
    data = get_amortization(property_id)
    if data is None:
        return {"config": None, "schedule": [], "summary": {}}
    return data


class MortgageConfigBody(BaseModel):
    property_id: int
    loan_amount: float
    annual_rate_pct: float
    term_months: int
    monthly_payment: float
    start_date: str
    appreciation_rate: float = 2.5


@router.post("/real-estate/mortgage-config")
async def api_mortgage_config(body: MortgageConfigBody):
    return save_mortgage_config(
        body.property_id,
        body.loan_amount,
        body.annual_rate_pct,
        body.term_months,
        body.monthly_payment,
        body.start_date,
        body.appreciation_rate,
    )


class PropertyCostBody(BaseModel):
    property_id: int
    cost_year: int
    cost_month: int
    amount: float
    memo: Optional[str] = None


@router.post("/real-estate/cost")
async def api_property_cost(body: PropertyCostBody):
    return upsert_property_cost(body.property_id, body.cost_year, body.cost_month, body.amount, body.memo)
