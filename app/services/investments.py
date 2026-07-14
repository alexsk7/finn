from app.queries import get_allocation_targets
from app.writer import (
    add_holding,
    delete_holding,
    get_all_holdings_raw,
    import_holdings_csv,
    import_snapshot_csv,
    import_transaction_csv,
    refresh_prices,
    save_snapshot,
    update_holding,
    update_price,
    upsert_allocation_target,
)


def normalize_holding_symbol(symbol: str, is_manual: bool) -> str:
    sym = symbol.strip().upper()
    if is_manual and not sym.startswith("M:"):
        raise ValueError("Manual holding symbols must start with 'M:'")
    if not is_manual and sym.startswith("M:"):
        raise ValueError("Non-manual symbols cannot start with 'M:'")
    return sym


def add_holding_validated(
    account_id: int,
    symbol: str,
    asset_class: str,
    shares: float,
    cost_basis: float,
    name: str | None,
    is_manual: bool,
):
    sym = normalize_holding_symbol(symbol, is_manual)
    return add_holding(account_id, sym, asset_class, shares, cost_basis, name, is_manual)


def update_holding_validated(
    holding_id: int,
    account_id: int,
    symbol: str,
    asset_class: str,
    shares: float,
    cost_basis: float,
    name: str | None,
    is_manual: bool,
):
    sym = normalize_holding_symbol(symbol, is_manual)
    return update_holding(holding_id, account_id, sym, asset_class, shares, cost_basis, name, is_manual)


__all__ = [
    "add_holding",
    "add_holding_validated",
    "delete_holding",
    "get_all_holdings_raw",
    "get_allocation_targets",
    "import_holdings_csv",
    "import_snapshot_csv",
    "import_transaction_csv",
    "refresh_prices",
    "save_snapshot",
    "normalize_holding_symbol",
    "update_holding",
    "update_holding_validated",
    "update_price",
    "upsert_allocation_target",
]
