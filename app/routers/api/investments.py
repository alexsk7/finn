from fastapi import APIRouter, HTTPException

from app.routers.api.overrides import runtime_override
from app.schemas.investments import (
    AllocationTargetBody,
    HoldingBody,
    HoldingsImportBody,
    PriceUpdate,
    SnapshotBody,
    SnapshotImportBody,
)
from app.services.investments import (
    add_holding,
    delete_holding,
    get_all_holdings_raw,
    get_allocation_targets,
    import_holdings_csv,
    import_snapshot_csv,
    refresh_prices,
    save_snapshot,
    update_holding,
    update_price,
    upsert_allocation_target,
)

router = APIRouter(tags=["investments"])


@router.get("/allocation-targets")
async def api_allocation_targets():
    return get_allocation_targets()


@router.post("/allocation-targets")
async def api_allocation_target_upsert(body: AllocationTargetBody):
    return upsert_allocation_target(body.asset_class, body.target_pct)


@router.get("/holdings")
async def api_holdings_all():
    return get_all_holdings_raw()


@router.post("/holdings")
async def api_holding_add(body: HoldingBody):
    sym = body.symbol.strip().upper()
    if body.is_manual and not sym.startswith("M:"):
        raise HTTPException(status_code=400, detail="Manual holding symbols must start with 'M:'")
    if not body.is_manual and sym.startswith("M:"):
        raise HTTPException(status_code=400, detail="Non-manual symbols cannot start with 'M:'")
    return add_holding(body.account_id, sym, body.asset_class, body.shares, body.cost_basis, body.name, body.is_manual)


@router.put("/holdings/{holding_id}")
async def api_holding_update(holding_id: int, body: HoldingBody):
    sym = body.symbol.strip().upper()
    if body.is_manual and not sym.startswith("M:"):
        raise HTTPException(status_code=400, detail="Manual holding symbols must start with 'M:'")
    if not body.is_manual and sym.startswith("M:"):
        raise HTTPException(status_code=400, detail="Non-manual symbols cannot start with 'M:'")
    return update_holding(
        holding_id,
        body.account_id,
        sym,
        body.asset_class,
        body.shares,
        body.cost_basis,
        body.name,
        body.is_manual,
    )


@router.delete("/holdings/{holding_id}")
async def api_holding_delete(holding_id: int):
    delete_holding(holding_id)
    return {"ok": True}


@router.post("/holdings/import-csv")
async def api_holdings_import_csv(body: HoldingsImportBody):
    return import_holdings_csv(body.csv_text, body.account_id)


@router.post("/prices/refresh")
async def api_prices_refresh():
    refresh_prices_fn = runtime_override("refresh_prices", refresh_prices)
    return refresh_prices_fn()


@router.post("/prices/manual")
async def api_price_manual(body: PriceUpdate):
    update_price(body.symbol, body.price)
    return {"ok": True, "symbol": body.symbol.upper(), "price": body.price}


@router.post("/snapshot")
async def api_snapshot(body: SnapshotBody):
    return save_snapshot(body.account_balances, body.snapshot_date, body.notes)


@router.post("/snapshots/import-csv")
async def api_snapshot_import_csv(body: SnapshotImportBody):
    return import_snapshot_csv(body.csv_text)
