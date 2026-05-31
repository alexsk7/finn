"""Fuzzy transaction CSV column mapper: field-name fuzzy matching + profile + optional ML model."""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

# Hardcoded confidence thresholds
HIGH_CONFIDENCE = 0.78
MEDIUM_CONFIDENCE = 0.58
MIN_MODEL_ANCHORS = 2
MIN_MODEL_CLASSES = 2

# Amount profiling heuristics: tuneable bounds for "typical" transaction values.
AMOUNT_MEDIAN_ABS_MIN = 0.0
AMOUNT_MEDIAN_ABS_MAX = 20000.0
AMOUNT_MEDIAN_HINT_IN_RANGE = 1.0
AMOUNT_MEDIAN_HINT_OUT_OF_RANGE = 0.6

TARGET_FIELDS = [
    "date",
    "amount",
    "direction",
    "category",
    "payee",
    "description",
    "memo",
    "account_id",
    "recurring",
]

REQUIRED_FIELDS = {"date", "amount"}

DIRECTION_TOKENS = {
    "debit",
    "dr",
    "withdrawal",
    "charge",
    "credit",
    "cr",
    "deposit",
    "income",
    "expense",
    "transfer",
}

BOOL_TOKENS = {"0", "1", "true", "false", "yes", "no"}


@dataclass
class ColumnProfile:
    null_rate: float
    date_rate: float
    numeric_rate: float
    bool_rate: float
    neg_rate: float
    median_abs: float
    mean_len: float
    unique_ratio: float
    direction_token_rate: float


_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y/%m/%d")


def _attach_date_fallback(
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

    for h in ordered:
        if h == primary:
            continue
        h_norm = _normalize_header(h)
        if "post" in h_norm or "posted" in h_norm:
            mapping["_date_fallback"] = h
            return


def _normalize_header(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'").lower()
    s = re.sub(r"[_\-/]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _sniff_delimiter(lines: list[str]) -> str:
    sample = "\n".join(lines[:8])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except Exception:
        return _best_delimiter_fallback(lines[:8])


def _best_delimiter_fallback(lines: list[str]) -> str:
    """Choose delimiter by quote-aware parse consistency across sample lines."""
    if not lines:
        return ","

    delimiters = [",", "\t", ";", "|"]
    scored: list[tuple[float, int, float, str]] = []

    for delim in delimiters:
        counts: list[int] = []
        try:
            for row in csv.reader(lines, delimiter=delim):
                n_cols = len(row)
                if n_cols > 1:
                    counts.append(n_cols)
        except Exception:
            counts = []

        if not counts:
            scored.append((0.0, 0, 0.0, delim))
            continue

        freq: dict[int, int] = {}
        for n_cols in counts:
            freq[n_cols] = freq.get(n_cols, 0) + 1

        mode_count = max(freq.values())
        consistency = mode_count / len(counts)
        avg_cols = sum(counts) / len(counts)
        scored.append((consistency, len(counts), avg_cols, delim))

    best = max(scored)
    return best[3]


def _parse_float(v: str) -> float | None:
    txt = (v or "").strip()
    if not txt:
        return None

    neg = False

    # Accounting-style negatives: (123.45), ($1,234.56), (€1.234,50)
    if txt.startswith("(") and txt.endswith(")"):
        neg = True
        txt = txt[1:-1].strip()

    # Handle leading/trailing explicit sign markers.
    if txt.startswith("-") or txt.endswith("-"):
        neg = True
    txt = txt.strip("+-")

    # Remove common currency symbols and whitespace separators.
    txt = re.sub(r"[$€£¥₹₽₩₪₦₱₨฿]", "", txt)
    txt = txt.replace("\u00a0", " ").replace(" ", "")

    # Remove trailing currency code (e.g. USD, EUR).
    txt = re.sub(r"(?i)([A-Z]{3})$", "", txt)
    txt = txt.strip()

    if not txt:
        return None

    # Normalize thousands/decimal separators for common US/EU formats.
    if "." in txt and "," in txt:
        if txt.rfind(".") > txt.rfind(","):
            # 1,234.56 -> 1234.56
            txt = txt.replace(",", "")
        else:
            # 1.234,56 -> 1234.56
            txt = txt.replace(".", "").replace(",", ".")
    elif "," in txt:
        if re.search(r",\d{1,2}$", txt):
            # 1234,56 -> 1234.56
            txt = txt.replace(",", ".")
        else:
            # 1,234 or 1,234,567 -> 1234 / 1234567
            txt = txt.replace(",", "")

    try:
        out = float(txt)
        if not math.isfinite(out):
            return None
        return -out if neg else out
    except Exception:
        return None


def _parse_date(v: str) -> bool:
    txt = (v or "").strip()
    if not txt:
        return False
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(txt, fmt)
            return True
        except Exception:
            continue
    return False


def _median_abs(values: list[float]) -> float:
    """Return median of absolute values; empty input yields 0.0."""
    if not values:
        return 0.0

    arr = sorted(abs(v) for v in values)
    n_vals = len(arr)
    mid = n_vals // 2
    if n_vals % 2 == 1:
        return arr[mid]
    return (arr[mid - 1] + arr[mid]) / 2


def _profile_column(values: list[str]) -> ColumnProfile:
    n = len(values) or 1
    stripped = [(v or "").strip() for v in values]
    non_empty = [v for v in stripped if v]

    null_rate = 1 - (len(non_empty) / n)
    date_hits = sum(1 for v in non_empty if _parse_date(v))
    numeric_vals = [_parse_float(v) for v in non_empty]
    numeric_clean = [v for v in numeric_vals if v is not None]
    bool_hits = sum(1 for v in non_empty if v.lower() in BOOL_TOKENS)

    neg_rate = 0.0
    if numeric_clean:
        neg_rate = sum(1 for v in numeric_clean if v < 0) / len(numeric_clean)

    median_abs = _median_abs(numeric_clean)

    mean_len = (sum(len(v) for v in non_empty) / len(non_empty)) if non_empty else 0.0
    unique_ratio = (len({v.lower() for v in non_empty}) / len(non_empty)) if non_empty else 0.0
    direction_token_rate = (
        sum(1 for v in non_empty if v.lower() in DIRECTION_TOKENS) / len(non_empty) if non_empty else 0.0
    )

    return ColumnProfile(
        null_rate=null_rate,
        date_rate=date_hits / n,
        numeric_rate=len(numeric_clean) / n,
        bool_rate=bool_hits / n,
        neg_rate=neg_rate,
        median_abs=median_abs,
        mean_len=mean_len,
        unique_ratio=unique_ratio,
        direction_token_rate=direction_token_rate,
    )


def _header_score(field: str, header: str) -> float:
    norm = _normalize_header(header)
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


def _profile_score(field: str, p: ColumnProfile) -> float:
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
            0.0, min(1.0, 0.55 * p.direction_token_rate + 0.25 * (1 - p.numeric_rate) + 0.2 * (1 - p.unique_ratio))
        )
    if field == "recurring":
        return max(0.0, min(1.0, 0.75 * p.bool_rate + 0.25 * (1 - p.unique_ratio)))
    if field == "account_id":
        return max(0.0, min(1.0, 0.55 * p.numeric_rate + 0.45 * (1 - p.unique_ratio)))
    if field == "category":
        return max(0.0, min(1.0, 0.45 * (1 - p.numeric_rate) + 0.3 * (1 - p.unique_ratio) + 0.25 * (1 - p.null_rate)))
    if field == "payee":
        return max(0.0, min(1.0, 0.5 * (1 - p.numeric_rate) + 0.3 * p.unique_ratio + 0.2 * (1 - p.null_rate)))
    if field in {"description", "memo"}:
        len_hint = min(1.0, p.mean_len / 40.0)
        return max(0.0, min(1.0, 0.45 * (1 - p.numeric_rate) + 0.35 * len_hint + 0.2 * p.unique_ratio))
    return 0.0


def _adaptive_blend_weights(
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


def _maybe_model_probs(
    profiles: dict[str, ColumnProfile], header_scores: dict[str, dict[str, float]]
) -> tuple[dict[str, dict[str, float]], dict[str, str | int | bool]]:
    """Optional weakly-supervised sklearn model; safely no-op if unavailable."""
    zero_probs = {h: {f: 0.0 for f in TARGET_FIELDS} for h in profiles}

    try:
        from sklearn.linear_model import LogisticRegression  # type: ignore
    except Exception:
        return (
            zero_probs,
            {
                "available": False,
                "status": "skipped_no_sklearn",
                "anchor_count": 0,
                "class_count": 0,
            },
        )

    anchors_x: list[list[float]] = []
    anchors_y: list[str] = []

    def vec(p: ColumnProfile) -> list[float]:
        return [
            p.null_rate,
            p.date_rate,
            p.numeric_rate,
            p.bool_rate,
            p.neg_rate,
            p.median_abs,
            p.mean_len,
            p.unique_ratio,
            p.direction_token_rate,
        ]

    for header, field_scores in header_scores.items():
        field = max(field_scores, key=lambda k: field_scores[k])
        score = field_scores[field]
        if score >= 0.92:
            anchors_x.append(vec(profiles[header]))
            anchors_y.append(field)

    anchor_count = len(anchors_x)
    class_count = len(set(anchors_y))

    if anchor_count < MIN_MODEL_ANCHORS or class_count < MIN_MODEL_CLASSES:
        return (
            zero_probs,
            {
                "available": False,
                "status": "skipped_insufficient_anchors",
                "anchor_count": anchor_count,
                "class_count": class_count,
            },
        )

    try:
        model = LogisticRegression(max_iter=300, multi_class="auto")
        model.fit(anchors_x, anchors_y)
        out: dict[str, dict[str, float]] = {}
        classes = list(model.classes_)
        for header, p in profiles.items():
            probs = model.predict_proba([vec(p)])[0]
            class_prob = {f: 0.0 for f in TARGET_FIELDS}
            for idx, cls in enumerate(classes):
                class_prob[str(cls)] = float(probs[idx])
            out[header] = class_prob
        return (
            out,
            {
                "available": True,
                "status": "trained",
                "anchor_count": anchor_count,
                "class_count": len(classes),
            },
        )
    except Exception:
        return (
            zero_probs,
            {
                "available": False,
                "status": "skipped_training_error",
                "anchor_count": anchor_count,
                "class_count": class_count,
            },
        )


def _prepare_csv_lines(csv_text: str) -> list[str]:
    """Drop blank lines and leading comment lines, preserving all post-header rows."""
    raw_lines = (csv_text or "").splitlines()

    # Skip blank and comment-only prologue before the header row.
    start = 0
    while start < len(raw_lines):
        candidate = raw_lines[start].strip()
        if not candidate or candidate.startswith("#"):
            start += 1
            continue
        break

    if start >= len(raw_lines):
        return []

    # Keep non-empty lines from header onward. Do not drop hash-prefixed data rows.
    return [line for line in raw_lines[start:] if line.strip()]


def detect_transaction_csv_mapping(csv_text: str) -> dict:
    lines = _prepare_csv_lines(csv_text)
    if not lines:
        return {
            "ok": False,
            "error": "Empty input",
            "mapping": {},
            "confidence": {},
            "needs_confirmation": True,
            "delimiter": ",",
            "preview": [],
        }

    delimiter = _sniff_delimiter(lines)
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delimiter)
    headers = list(reader.fieldnames or [])
    rows = list(reader)
    sample_rows = rows[:120]

    if not headers:
        return {
            "ok": False,
            "error": "Could not detect CSV header row",
            "mapping": {},
            "confidence": {},
            "needs_confirmation": True,
            "delimiter": delimiter,
            "preview": [],
        }

    # Pure fuzzy + profile scoring (no exact-alias fast path).
    profiles = {h: _profile_column([(r.get(h, "") or "") for r in sample_rows]) for h in headers}

    header_scores = {h: {f: _header_score(f, h) for f in TARGET_FIELDS} for h in headers}
    model_probs, model_meta = _maybe_model_probs(profiles, header_scores)
    model_available = bool(model_meta.get("available", False))

    # Blend fuzzy header and profile-model confidence
    blended: dict[str, dict[str, float]] = {}
    for h in headers:
        blended[h] = {}
        p = profiles[h]
        for f in TARGET_FIELDS:
            profile_component = _profile_score(f, p)
            model_component = model_probs[h][f]
            header_component = header_scores[h][f]
            header_w, profile_w, model_w = _adaptive_blend_weights(
                header_component,
                profile_component,
                model_component,
                model_available=model_available,
            )
            blended[h][f] = header_w * header_component + profile_w * profile_component + model_w * model_component

    # One-to-one assignment by global best scores
    candidates: list[tuple[float, str, str]] = []
    for h in headers:
        for f in TARGET_FIELDS:
            candidates.append((blended[h][f], f, h))
    candidates.sort(reverse=True)

    mapping: dict[str, str] = {}
    confidence: dict[str, float] = {}
    used_headers: set[str] = set()

    for score, field, header in candidates:
        if field in mapping or header in used_headers:
            continue
        if score < MEDIUM_CONFIDENCE:
            continue
        mapping[field] = header
        confidence[field] = round(score, 3)
        used_headers.add(header)

    # Ensure required fields always get a best-effort mapping.
    for field in REQUIRED_FIELDS:
        if field in mapping:
            continue
        available_headers = [h for h in headers if h not in used_headers]
        if not available_headers:
            preview = []
            for row in rows[:5]:
                preview.append({h: (row.get(h, "") or "") for h in headers})
            return {
                "ok": False,
                "error": "Not enough distinct headers to map required fields without reusing columns",
                "mapping": mapping,
                "confidence": confidence,
                "needs_confirmation": True,
                "delimiter": delimiter,
                "headers": headers,
                "preview": preview,
                "thresholds": {
                    "high": HIGH_CONFIDENCE,
                    "medium": MEDIUM_CONFIDENCE,
                },
                "strategy": "fuzzy_match",
                "model": model_meta,
            }
        best_h = max(available_headers, key=lambda h: blended[h][field])
        mapping[field] = best_h
        confidence[field] = round(blended[best_h][field], 3)
        used_headers.add(best_h)

    # Post date fallback for date parsing when transaction date exists.
    _attach_date_fallback(mapping, headers, {h: blended[h]["date"] for h in headers})

    # Alternatives for UI explanation.
    alternatives: dict[str, list[dict]] = {}
    for field in TARGET_FIELDS:
        ranked = sorted(headers, key=lambda h: blended[h][field], reverse=True)[:3]
        alternatives[field] = [{"header": h, "score": round(blended[h][field], 3)} for h in ranked]

    low_required = any(confidence.get(f, 0.0) < MEDIUM_CONFIDENCE for f in REQUIRED_FIELDS)
    low_any = any(v < HIGH_CONFIDENCE for k, v in confidence.items() if not k.startswith("_"))

    preview = []
    for row in rows[:5]:
        preview.append({h: (row.get(h, "") or "") for h in headers})

    return {
        "ok": True,
        "mapping": mapping,
        "confidence": confidence,
        "alternatives": alternatives,
        "needs_confirmation": bool(low_required or low_any),
        "delimiter": delimiter,
        "headers": headers,
        "preview": preview,
        "model": model_meta,
        "thresholds": {
            "high": HIGH_CONFIDENCE,
            "medium": MEDIUM_CONFIDENCE,
        },
        "strategy": "fuzzy_match",
    }
