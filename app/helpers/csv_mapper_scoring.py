"""Scoring helpers for transaction CSV mapper."""

from __future__ import annotations

from difflib import SequenceMatcher

from app.helpers.csv_mapper_constants import (
    AMOUNT_MEDIAN_ABS_MAX,
    AMOUNT_MEDIAN_ABS_MIN,
    AMOUNT_MEDIAN_HINT_IN_RANGE,
    AMOUNT_MEDIAN_HINT_OUT_OF_RANGE,
)
from app.helpers.csv_mapper_parsing import normalize_header
from app.helpers.csv_mapper_types import ColumnProfile


def attach_date_fallback(
    mapping: dict[str, str], headers: list[str], score_lookup: dict[str, float] | None = None
) -> None:
    """Attach post-date fallback header when available and not already selected as primary date."""
    if not headers:
        return

    if score_lookup is None:
        # Prefer explicit post/posted headers in original order.
        ordered = headers
    else:
        ordered = sorted(headers, key=lambda h: score_lookup.get(h, 0.0), reverse=True)

    primary = mapping.get("date")
    if not primary:
        return

    def _is_transaction_like(header: str) -> bool:
        norm = normalize_header(header)
        tokens = set(norm.split())
        return "transaction" in norm or "txn" in tokens or "dt" in tokens

    def _is_post_like(header: str) -> bool:
        norm = normalize_header(header)
        return "post" in norm or "posted" in norm

    transaction_headers = [h for h in headers if _is_transaction_like(h)]
    post_headers = [h for h in headers if _is_post_like(h)]

    # If date selected a post/posted column, promote a transaction-like column to primary.
    if _is_post_like(primary) and transaction_headers:
        if score_lookup is None:
            mapping["date"] = transaction_headers[0]
        else:
            mapping["date"] = max(transaction_headers, key=lambda h: score_lookup.get(h, 0.0))
        primary = mapping["date"]

    for h in ordered:
        if h == primary:
            continue
        if h in post_headers:
            mapping["_date_fallback"] = h
            return


def header_score(field: str, header: str) -> float:
    norm = normalize_header(header)
    tokens = set(norm.split())
    # Pure fuzzy matching: compare header against field name.
    best = SequenceMatcher(None, norm, field).ratio()

    # Field-specific heuristics for clarity.
    if field == "date":
        # Strongly prefer transaction/txn date over posted date.
        if "transaction" in norm or "txn" in tokens or "dt" in tokens:
            best += 0.35
        elif "post" in norm or "posted" in norm:
            best -= 0.15
    elif field == "amount":
        # Boost for numeric/value indicators.
        if tokens.intersection({"amount", "amt", "value", "price", "usd", "debit", "credit"}):
            best += 0.30
    elif field == "direction":
        # Boost for type/direction keywords.
        if tokens.intersection({"type", "direction", "dr", "credit", "debit", "cr"}):
            best += 0.10
    elif field == "payee":
        # Boost for merchant/vendor indicators.
        if "merchant" in norm or "vendor" in norm or "counterparty" in norm:
            best += 0.10

    return max(0.0, min(1.0, best))


def profile_score(field: str, p: ColumnProfile) -> float:
    if field == "date":
        return max(0.0, min(1.0, 0.85 * p.date_rate + 0.1 * (1 - p.null_rate) + 0.05 * (1 - p.numeric_rate)))
    if field == "amount":
        median_hint = (
            AMOUNT_MEDIAN_HINT_IN_RANGE
            if AMOUNT_MEDIAN_ABS_MIN < p.median_abs < AMOUNT_MEDIAN_ABS_MAX
            else AMOUNT_MEDIAN_HINT_OUT_OF_RANGE
        )
        return max(0.0, min(1.0, 0.65 * p.numeric_rate + 0.2 * (1 - p.null_rate) + 0.15 * median_hint))
    if field == "direction":
        return max(
            0.0,
            min(1.0, 0.55 * p.direction_token_rate + 0.25 * (1 - p.numeric_rate) + 0.2 * (1 - p.unique_ratio)),
        )
    if field == "recurring":
        return max(0.0, min(1.0, 0.75 * p.bool_rate + 0.25 * (1 - p.unique_ratio)))
    if field == "account_id":
        return max(0.0, min(1.0, 0.55 * p.numeric_rate + 0.45 * (1 - p.unique_ratio)))
    if field == "category":
        return max(
            0.0,
            min(1.0, 0.45 * (1 - p.numeric_rate) + 0.3 * (1 - p.unique_ratio) + 0.25 * (1 - p.null_rate)),
        )
    if field == "payee":
        return max(0.0, min(1.0, 0.5 * (1 - p.numeric_rate) + 0.3 * p.unique_ratio + 0.2 * (1 - p.null_rate)))
    if field in {"description", "memo"}:
        len_hint = min(1.0, p.mean_len / 40.0)
        return max(0.0, min(1.0, 0.45 * (1 - p.numeric_rate) + 0.35 * len_hint + 0.2 * p.unique_ratio))
    return 0.0


def adaptive_blend_weights(
    header_component: float,
    profile_component: float,
    model_component: float,
    *,
    model_available: bool,
) -> tuple[float, float, float]:
    """Compute dynamic blend weights for header/profile/model components.

    - Strong header signals increase header influence.
    - Profile remains a stabilizing component.
    - Model contributes only when available and confident.
    """
    header_component = max(0.0, min(1.0, header_component))
    profile_component = max(0.0, min(1.0, profile_component))
    model_component = max(0.0, min(1.0, model_component))

    # Header dominates when lexical evidence is strong.
    header_w = 0.45 + 0.35 * header_component
    profile_w = 1.0 - header_w

    # Strong profile evidence should reclaim some weight from header confidence.
    # This keeps profiling relevant for ambiguous or weakly named headers.
    profile_boost = 0.15 * profile_component
    header_w = max(0.0, header_w - profile_boost)
    profile_w += profile_boost
    model_w = 0.0

    # Introduce model weight only when predictions are available.
    if model_available:
        # Scale model contribution by confidence, capped to keep explainability.
        model_w = 0.2 * model_component
        profile_w -= model_w

    # Keep profile as a minimum anchor to avoid overfitting to header/model noise.
    if profile_w < 0.1:
        deficit = 0.1 - profile_w
        profile_w = 0.1
        header_w = max(0.0, header_w - deficit)

    # Normalize to exactly 1.0.
    total = header_w + profile_w + model_w
    if total <= 0:
        return 0.6, 0.4, 0.0
    return header_w / total, profile_w / total, model_w / total
