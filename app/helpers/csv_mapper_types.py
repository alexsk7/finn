"""Typed data structures used by transaction CSV mapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict


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

    def __post_init__(self) -> None:
        ratio_fields = {
            "null_rate": self.null_rate,
            "date_rate": self.date_rate,
            "numeric_rate": self.numeric_rate,
            "bool_rate": self.bool_rate,
            "neg_rate": self.neg_rate,
            "unique_ratio": self.unique_ratio,
            "direction_token_rate": self.direction_token_rate,
        }
        for name, value in ratio_fields.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be within [0.0, 1.0], got {value}")

        if self.median_abs < 0.0:
            raise ValueError(f"median_abs must be >= 0.0, got {self.median_abs}")
        if self.mean_len < 0.0:
            raise ValueError(f"mean_len must be >= 0.0, got {self.mean_len}")


class CsvThresholds(TypedDict):
    high: float
    medium: float


class CsvAlternative(TypedDict):
    header: str
    score: float


class CsvModelMeta(TypedDict):
    available: bool
    status: str
    anchor_count: int
    class_count: int


class CsvMappingResult(TypedDict, total=False):
    ok: bool
    error: str
    mapping: dict[str, str]
    confidence: dict[str, float]
    alternatives: dict[str, list[CsvAlternative]]
    needs_confirmation: bool
    delimiter: str
    headers: list[str]
    preview: list[dict[str, str]]
    thresholds: CsvThresholds
    strategy: str
    model: CsvModelMeta
