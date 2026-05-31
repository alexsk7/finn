from typing import Optional

from pydantic import BaseModel


class AccountBody(BaseModel):
    name: str
    institution: str
    type: str
    notes: Optional[str] = None
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    opening_balance: Optional[float] = None


class AccountUpdateBody(BaseModel):
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    opening_balance: Optional[float] = None
