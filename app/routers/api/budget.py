from typing import Optional

from fastapi import APIRouter, HTTPException

from app.schemas.budget import (
    BudgetCategoryBody,
    BudgetCategoryUpdate,
    BudgetMonthBody,
    BudgetMonthCopyBody,
)
from app.services.budget import (
    add_budget_category,
    copy_budget_month,
    delete_budget_category,
    get_budget_categories_full,
    get_budget_month,
    save_budget_month,
    update_budget_category,
)

router = APIRouter(tags=["budget"])


@router.get("/budget")
async def api_budget(month: Optional[str] = None):
    try:
        return get_budget_month(month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/budget-categories")
async def api_budget_categories():
    return get_budget_categories_full()


@router.post("/budget-categories")
async def api_budget_category_add(body: BudgetCategoryBody):
    return add_budget_category(body.name, body.monthly_target, body.direction)


@router.put("/budget-categories/{category_id}")
async def api_budget_category_update(category_id: int, body: BudgetCategoryUpdate):
    return update_budget_category(category_id, body.name, body.monthly_target)


@router.delete("/budget-categories/{category_id}")
async def api_budget_category_delete(category_id: int):
    delete_budget_category(category_id)
    return {"ok": True}


@router.put("/budget/months/{month}")
async def api_budget_month_save(month: str, body: BudgetMonthBody):
    try:
        items = [i.model_dump() if hasattr(i, "model_dump") else i.dict() for i in body.items]
        return save_budget_month(month, items, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/budget/months/{month}/copy")
async def api_budget_month_copy(month: str, body: BudgetMonthCopyBody):
    try:
        return copy_budget_month(month, body.source_month, body.overwrite)
    except ValueError as e:
        status_code = 409 if "already has a plan" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))
