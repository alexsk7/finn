"""Hybrid transaction CSV column mapper: fuzzy header + profile model."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher

# Hardcoded confidence thresholds
HIGH_CONFIDENCE = 0.78
MEDIUM_CONFIDENCE = 0.58

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

FIELD_ALIASES = {
    "date": {
        "date",
        "txn_date",
        "transaction_date",
        "transaction date",
        "posted_date",
        "posted date",
        "post_date",
        "post date",
        "posting_date",
        "posting date",
    },
    "amount": {
        "amount",
        "amt",
        "debit_amount",
        "debit amount",
        "credit_amount",
        "credit amount",
        "value",
    },
    "direction": {
        "direction",
        "type",
        "dr_cr",
        "dr/cr",
        "transaction_type",
        "transaction type",
        "credit_debit",
        "credit/debit",
    },
    "category": {"category", "cat", "merchant_category", "merchant category"},
    "payee": {"payee", "merchant", "vendor", "name", "counterparty"},
    "description": {"description", "desc", "details", "narrative"},
    "memo": {"memo", "note", "notes", "reference", "ref"},
    "account_id": {"account_id", "account id", "account", "account_number", "account number"},
    "recurring": {"recurring", "is_recurring", "repeat", "autopay"},
}

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


def _attach_date_fallback(mapping: dict[str, str], headers: list[str], score_lookup: dict[str, float] | None = None) -> None:
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


def _exact_alias_mapping(headers: list[str]) -> tuple[dict[str, str], dict[str, float]]:
    """Map headers by exact alias only (normalized exact equality, no fuzzy scoring)."""
    mapping: dict[str, str] = {}
    confidence: dict[str, float] = {}
    used_headers: set[str] = set()

    norm_headers = {h: _normalize_header(h) for h in headers}

    # Keep deterministic field ordering.
    for field in TARGET_FIELDS:
        aliases = {_normalize_header(a) for a in FIELD_ALIASES[field]}
        for h in headers:
            if h in used_headers:
                continue
            if norm_headers[h] in aliases:
                mapping[field] = h
                confidence[field] = 1.0
                used_headers.add(h)
                break

    _attach_date_fallback(mapping, headers)
    return mapping, confidence


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
        if "\t" in sample and sample.count("\t") > sample.count(","):
            return "\t"
        return ","


def _parse_float(v: str) -> float | None:
    txt = (v or "").strip()
    if not txt:
        return None
    txt = txt.replace("$", "").replace(",", "")
    if txt.startswith("(") and txt.endswith(")"):
        txt = "-" + txt[1:-1]
    try:
        return float(txt)
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

    median_abs = 0.0
    if numeric_clean:
        arr = sorted(abs(v) for v in numeric_clean)
        mid = len(arr) // 2
        median_abs = arr[mid] if len(arr) % 2 else (arr[mid - 1] + arr[mid]) / 2

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
    aliases = FIELD_ALIASES[field]

    best = 0.0
    for alias in aliases:
        alias_n = _normalize_header(alias)
        if norm == alias_n:
            best = max(best, 1.0)
            continue
        if alias_n in norm or norm in alias_n:
            best = max(best, 0.9)
            continue
        best = max(best, SequenceMatcher(None, norm, alias_n).ratio())

    # Prefer transaction date over posted date for primary mapping.
    if field == "date":
        if "transaction" in norm or norm.startswith("txn"):
            best += 0.08
        if "post" in norm or "posted" in norm:
            best -= 0.06

    return max(0.0, min(1.0, best))


def _profile_score(field: str, p: ColumnProfile) -> float:
    if field == "date":
        return max(0.0, min(1.0, 0.85 * p.date_rate + 0.1 * (1 - p.null_rate) + 0.05 * (1 - p.numeric_rate)))
    if field == "amount":
        median_hint = 1.0 if 0 < p.median_abs < 20000 else 0.6
        return max(0.0, min(1.0, 0.65 * p.numeric_rate + 0.2 * (1 - p.null_rate) + 0.15 * median_hint))
    if field == "direction":
        return max(0.0, min(1.0, 0.55 * p.direction_token_rate + 0.25 * (1 - p.numeric_rate) + 0.2 * (1 - p.unique_ratio)))
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


def _maybe_model_probs(profiles: dict[str, ColumnProfile], header_scores: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    """Optional weakly-supervised sklearn model; safely no-op if unavailable."""
    try:
        from sklearn.linear_model import LogisticRegression  # type: ignore
    except Exception:
        return {h: {f: 0.0 for f in TARGET_FIELDS} for h in profiles}

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

    if len(anchors_x) < 4 or len(set(anchors_y)) < 2:
        return {h: {f: 0.0 for f in TARGET_FIELDS} for h in profiles}

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
        return out
    except Exception:
        return {h: {f: 0.0 for f in TARGET_FIELDS} for h in profiles}


def detect_transaction_csv_mapping(csv_text: str) -> dict:
    lines: list[str] = [
        line for line in (csv_text or "").strip().splitlines() if line.strip() and not line.strip().startswith("#")
    ]
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

    # Fast path: exact alias mapping with no model/scoring overhead.
    exact_mapping, exact_confidence = _exact_alias_mapping(headers)
    exact_required_ok = all(f in exact_mapping for f in REQUIRED_FIELDS)
    if exact_required_ok:
        preview = []
        for row in rows[:5]:
            preview.append({h: (row.get(h, "") or "") for h in headers})

        alternatives: dict[str, list[dict]] = {}
        for field in TARGET_FIELDS:
            alternatives[field] = [{"header": exact_mapping[field], "score": 1.0}] if field in exact_mapping else []

        return {
            "ok": True,
            "mapping": exact_mapping,
            "confidence": exact_confidence,
            "alternatives": alternatives,
            "needs_confirmation": False,
            "delimiter": delimiter,
            "headers": headers,
            "preview": preview,
            "thresholds": {
                "high": HIGH_CONFIDENCE,
                "medium": MEDIUM_CONFIDENCE,
            },
            "strategy": "exact_alias",
        }

    profiles = {
        h: _profile_column([(r.get(h, "") or "") for r in sample_rows])
        for h in headers
    }

    header_scores = {
        h: {f: _header_score(f, h) for f in TARGET_FIELDS}
        for h in headers
    }
    model_probs = _maybe_model_probs(profiles, header_scores)

    # Blend fuzzy header and profile-model confidence
    blended: dict[str, dict[str, float]] = {}
    for h in headers:
        blended[h] = {}
        p = profiles[h]
        for f in TARGET_FIELDS:
            profile_component = _profile_score(f, p)
            model_component = model_probs[h][f]
            blended[h][f] = 0.55 * header_scores[h][f] + 0.3 * profile_component + 0.15 * model_component

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
        best_h = max(headers, key=lambda h: blended[h][field])
        mapping[field] = best_h
        confidence[field] = round(blended[best_h][field], 3)

    # Post date fallback for date parsing when transaction date exists.
    _attach_date_fallback(mapping, headers, {h: blended[h]["date"] for h in headers})

    # Alternatives for UI explanation.
    alternatives: dict[str, list[dict]] = {}
    for field in TARGET_FIELDS:
        ranked = sorted(headers, key=lambda h: blended[h][field], reverse=True)[:3]
        alternatives[field] = [
            {"header": h, "score": round(blended[h][field], 3)}
            for h in ranked
        ]

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
        "thresholds": {
            "high": HIGH_CONFIDENCE,
            "medium": MEDIUM_CONFIDENCE,
        },
        "strategy": "hybrid_fallback",
    }
