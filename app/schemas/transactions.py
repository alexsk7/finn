from typing import Optional

from pydantic import BaseModel


class TransactionBody(BaseModel):
    txn_date: str
    amount: float
    direction: str
    category: str = "uncategorized"
    payee: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[int] = None
    recurring: bool = False


class TransactionUpdateBody(BaseModel):
    txn_date: str
    amount: float
    direction: str
    category: str = "uncategorized"
    payee: Optional[str] = None
    description: Optional[str] = None
    account_id: Optional[int] = None


class TransactionBulkCategoryBody(BaseModel):
    ids: list[int]
    category: str = "uncategorized"


class TransactionImportBody(BaseModel):
    csv_text: str
    account_id: Optional[int] = None
    field_mapping: Optional[dict[str, str]] = None


class TransactionDetectBody(BaseModel):
    csv_text: str
