from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.csv_mapper import detect_transaction_csv_mapping
from app.routers.api.overrides import runtime_override
from app.services.reads import get_transactions
from app.services.writes import (
    add_transaction,
    bulk_update_transaction_category,
    delete_transaction,
    import_transaction_csv,
    update_transaction,
)

router = APIRouter(tags=["transactions"])


@router.get("/transactions")
async def api_transactions_list(
    limit: int = 100,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    account_id: Optional[int] = None,
    month: Optional[str] = None,
):
    try:
        return get_transactions(limit, category, direction, account_id, month)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class TransactionBody(BaseModel):
    txn_date: str
    amount: float
    direction: str
    category: str = "uncategorized"
    payee: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[int] = None
    recurring: bool = False


@router.post("/transactions")
async def api_transaction_post(txn: TransactionBody):
    return add_transaction(
        txn.txn_date,
        txn.amount,
        txn.direction,
        txn.category,
        txn.payee,
        txn.description,
        txn.account_id,
        txn.recurring,
    )


class TransactionUpdateBody(BaseModel):
    txn_date: str
    amount: float
    direction: str
    category: str = "uncategorized"
    payee: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[int] = None


@router.put("/transactions/{txn_id}")
async def api_transaction_update(txn_id: int, body: TransactionUpdateBody):
    return update_transaction(
        txn_id,
        body.txn_date,
        body.amount,
        body.direction,
        body.category,
        body.payee,
        body.description,
        body.account_id,
    )


class TransactionBulkCategoryBody(BaseModel):
    ids: list[int]
    category: str = "uncategorized"


@router.post("/transactions/bulk-category")
async def api_transaction_bulk_category(body: TransactionBulkCategoryBody):
    return bulk_update_transaction_category(body.ids, body.category)


@router.delete("/transactions/{txn_id}")
async def api_transaction_delete(txn_id: int):
    delete_transaction(txn_id)
    return {"ok": True}


class TransactionImportBody(BaseModel):
    csv_text: str
    account_id: Optional[int] = None
    field_mapping: Optional[dict[str, str]] = None


class TransactionDetectBody(BaseModel):
    csv_text: str


@router.post("/transactions/detect-columns")
async def api_transaction_detect_columns(body: TransactionDetectBody):
    detect_fn = runtime_override("detect_transaction_csv_mapping", detect_transaction_csv_mapping)
    return detect_fn(body.csv_text)


@router.post("/transactions/import-csv")
async def api_transaction_import_csv(body: TransactionImportBody):
    import_fn = runtime_override("import_transaction_csv", import_transaction_csv)
    return import_fn(body.csv_text, body.account_id, body.field_mapping)
