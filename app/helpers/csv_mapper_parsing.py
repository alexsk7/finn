"""Parsing and profiling helpers for transaction CSV mapper."""

from __future__ import annotations

import math
import re
from datetime import datetime

from app.helpers.csv_mapper_constants import BOOL_TOKENS_LOWER, DIRECTION_TOKENS
from app.helpers.csv_mapper_types import ColumnProfile

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
)


def normalize_header(s: str) -> str:
    s = (s or "").strip().strip('"').strip("'").lower()
    s = re.sub(r"[_\-/]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def parse_float(v: str) -> float | None:
    txt = (v or "").strip()
    if not txt:
        return None

    neg = False

    # Accounting-style negatives: (123.45), ($1,234.56), (EUR1.234,50)
    if txt.startswith("(") and txt.endswith(")"):
        neg = True
        txt = txt[1:-1].strip()

    # Handle leading/trailing explicit sign markers.
    if txt.startswith("-") or txt.endswith("-"):
        neg = True
    txt = txt.strip("+-")

    # Remove common currency symbols and whitespace separators.
    txt = re.sub(r"[\u0024\u20AC\u00A3\u00A5\u20B9\u20BD\u20A9\u20AA\u20A6\u20B1\u20A8\u0E3F]", "", txt)
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


def parse_date(v: str) -> bool:
    txt = (v or "").strip()
    if not txt:
        return False
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(txt, fmt)
            return True
        except Exception:
            continue

    # Fall back to ISO-8601 parsing for timezone/fractional second variants.
    iso_txt = txt
    if iso_txt.endswith("Z"):
        iso_txt = f"{iso_txt[:-1]}+00:00"
    try:
        datetime.fromisoformat(iso_txt)
        return True
    except Exception:
        return False


def median_abs(values: list[float]) -> float:
    """Return median of absolute values; empty input yields 0.0."""
    if not values:
        return 0.0

    arr = sorted(abs(v) for v in values)
    n_vals = len(arr)
    mid = n_vals // 2
    if n_vals % 2 == 1:
        return arr[mid]
    return (arr[mid - 1] + arr[mid]) / 2


def profile_column(values: list[str]) -> ColumnProfile:
    n = len(values) or 1
    stripped = [(v or "").strip() for v in values]
    non_empty = [v for v in stripped if v]

    null_rate = 1 - (len(non_empty) / n)
    date_hits = sum(1 for v in non_empty if parse_date(v))
    numeric_vals = [parse_float(v) for v in non_empty]
    numeric_clean = [v for v in numeric_vals if v is not None]
    bool_hits = sum(1 for v in non_empty if v.lower() in BOOL_TOKENS_LOWER)

    neg_rate = 0.0
    if numeric_clean:
        neg_rate = sum(1 for v in numeric_clean if v < 0) / len(numeric_clean)

    median_abs_value = median_abs(numeric_clean)

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
        median_abs=median_abs_value,
        mean_len=mean_len,
        unique_ratio=unique_ratio,
        direction_token_rate=direction_token_rate,
    )


def prepare_csv_lines(csv_text: str) -> list[str]:
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
