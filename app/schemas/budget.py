from typing import Optional

from pydantic import BaseModel


class BudgetCategoryBody(BaseModel):
    name: str
    monthly_target: float
    direction: str = "expense"


class BudgetCategoryUpdate(BaseModel):
    name: str
    monthly_target: float


class BudgetMonthItemBody(BaseModel):
    category_id: int
    planned_amount: float = 0


class BudgetMonthBody(BaseModel):
    items: list[BudgetMonthItemBody]
    notes: Optional[str] = None


class BudgetMonthCopyBody(BaseModel):
    source_month: str
    overwrite: bool = False
