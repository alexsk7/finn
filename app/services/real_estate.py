from app.queries import get_amortization, get_real_estate
from app.writer import (
    add_real_estate,
    delete_real_estate,
    link_real_estate_account,
    save_mortgage_config,
    update_real_estate,
    upsert_property_cost,
)


def get_amortization_or_empty(property_id: int) -> dict:
    data = get_amortization(property_id)
    if data is None:
        return {"config": None, "schedule": [], "summary": {}}
    return data


__all__ = [
    "add_real_estate",
    "delete_real_estate",
    "get_amortization",
    "get_amortization_or_empty",
    "get_real_estate",
    "link_real_estate_account",
    "save_mortgage_config",
    "update_real_estate",
    "upsert_property_cost",
]
