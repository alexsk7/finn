"""Constants used by transaction CSV mapper."""

from __future__ import annotations

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

# Input guardrails to avoid pathological memory usage on oversized CSV payloads.
MAX_CSV_TEXT_CHARS = 10 * 1024 * 1024
MAX_CSV_LINES = 200000

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
    "in",
    "out",
    "inflow",
    "outflow",
    "spend",
    "purchase",
    "payment",
    "send",
    "receive",
}

BOOL_TOKENS = {"0", "1", "true", "false", "yes", "no"}
BOOL_TOKENS_LOWER = {token.lower() for token in BOOL_TOKENS}
