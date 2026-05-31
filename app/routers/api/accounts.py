from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services.accounts import (
    add_account,
    delete_account,
    get_account_by_id,
    get_account_transactions,
    get_accounts_summary,
    update_account,
)

router = APIRouter(tags=["accounts"])


@router.get("/accounts")
async def api_accounts():
    return get_accounts_summary()


@router.get("/accounts/{account_id}")
async def api_account_detail(account_id: int):
    acct = get_account_by_id(account_id)
    if acct is None:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    return acct


@router.get("/accounts/{account_id}/transactions")
async def api_account_transactions(account_id: int, limit: int = 500):
    return get_account_transactions(account_id, limit)


class AccountBody(BaseModel):
    name: str
    institution: str
    type: str
    notes: Optional[str] = None
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    opening_balance: Optional[float] = None


@router.post("/accounts")
async def api_account_add(body: AccountBody):
    return add_account(
        body.name,
        body.institution,
        body.type,
        body.notes,
        body.interest_rate,
        body.minimum_payment,
        body.opening_balance,
    )


class AccountUpdateBody(BaseModel):
    interest_rate: Optional[float] = None
    minimum_payment: Optional[float] = None
    opening_balance: Optional[float] = None


@router.put("/accounts/{account_id}")
async def api_account_update(account_id: int, body: AccountUpdateBody):
    return update_account(account_id, body.interest_rate, body.minimum_payment, body.opening_balance)


@router.delete("/accounts/{account_id}")
async def api_account_delete(account_id: int):
    return delete_account(account_id)
