from typing import Optional

from fastapi import APIRouter, HTTPException

from app.routers.api.overrides import runtime_override
from app.schemas.transactions import (
    TransactionBody,
    TransactionBulkCategoryBody,
    TransactionDetectBody,
    TransactionImportBody,
    TransactionUpdateBody,
)
from app.services.transactions import (
    add_transaction,
    bulk_update_transaction_category,
    delete_transaction,
    detect_transaction_csv_mapping,
    get_transactions,
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


@router.post("/transactions/bulk-category")
async def api_transaction_bulk_category(body: TransactionBulkCategoryBody):
    return bulk_update_transaction_category(body.ids, body.category)


@router.delete("/transactions/{txn_id}")
async def api_transaction_delete(txn_id: int):
    delete_transaction(txn_id)
    return {"ok": True}


@router.post("/transactions/detect-columns")
async def api_transaction_detect_columns(body: TransactionDetectBody):
    detect_fn = runtime_override("detect_transaction_csv_mapping", detect_transaction_csv_mapping)
    return detect_fn(body.csv_text)


@router.post("/transactions/import-csv")
async def api_transaction_import_csv(body: TransactionImportBody):
    import_fn = runtime_override("import_transaction_csv", import_transaction_csv)
    return import_fn(body.csv_text, body.account_id, body.field_mapping)
