from typing import Optional

from pydantic import BaseModel


class AllocationTargetBody(BaseModel):
    asset_class: str
    target_pct: float


class HoldingBody(BaseModel):
    account_id: int
    symbol: str
    asset_class: str
    shares: float
    cost_basis: float
    name: Optional[str] = None
    is_manual: bool = False


class HoldingsImportBody(BaseModel):
    csv_text: str
    account_id: int


class PriceUpdate(BaseModel):
    symbol: str
    price: float


class SnapshotBody(BaseModel):
    account_balances: list[dict]
    snapshot_date: Optional[str] = None
    notes: Optional[str] = None


class SnapshotImportBody(BaseModel):
    csv_text: str
