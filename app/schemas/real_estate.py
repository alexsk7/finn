from typing import Optional

from pydantic import BaseModel


class RealEstateUpdate(BaseModel):
    property_id: int
    estimated_value: float
    mortgage_balance: float


class RealEstateAdd(BaseModel):
    name: str
    estimated_value: float
    mortgage_balance: float = 0
    address: Optional[str] = None
    purchase_price: float = 0
    purchase_date: Optional[str] = None
    account_id: Optional[int] = None


class RealEstateLinkBody(BaseModel):
    account_id: Optional[int] = None


class MortgageConfigBody(BaseModel):
    property_id: int
    loan_amount: float
    annual_rate_pct: float
    term_months: int
    monthly_payment: float
    start_date: str
    appreciation_rate: float = 2.5


class PropertyCostBody(BaseModel):
    property_id: int
    cost_year: int
    cost_month: int
    amount: float
    memo: Optional[str] = None
