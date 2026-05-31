"""Fuzzy transaction CSV column mapper orchestrator.

This module keeps the historical public surface for imports/tests while
delegating most implementation details into app.helpers.
"""

from __future__ import annotations

import csv
import io

from app.helpers import csv_mapper_constants as constants
from app.helpers import csv_mapper_io as io_helpers
from app.helpers import csv_mapper_model as model_helpers
from app.helpers import csv_mapper_parsing as parsing_helpers
from app.helpers import csv_mapper_scoring as scoring_helpers
from app.helpers import csv_mapper_types as mapper_types


def detect_transaction_csv_mapping(csv_text: str) -> mapper_types.CsvMappingResult:
    if len(csv_text or "") > constants.MAX_CSV_TEXT_CHARS:
        return {
            "ok": False,
            "error": f"CSV input exceeds max size ({constants.MAX_CSV_TEXT_CHARS} characters)",
            "mapping": {},
            "confidence": {},
            "needs_confirmation": True,
            "delimiter": ",",
            "preview": [],
        }

    if (csv_text or "").count("\n") + 1 > constants.MAX_CSV_LINES:
        return {
            "ok": False,
            "error": f"CSV input exceeds max line count ({constants.MAX_CSV_LINES})",
            "mapping": {},
            "confidence": {},
            "needs_confirmation": True,
            "delimiter": ",",
            "preview": [],
        }

    lines = parsing_helpers.prepare_csv_lines(csv_text)
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

    delimiter = io_helpers.sniff_delimiter(lines)
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

    if not rows:
        return {
            "ok": False,
            "error": "No data rows found",
            "mapping": {},
            "confidence": {},
            "needs_confirmation": True,
            "delimiter": delimiter,
            "headers": headers,
            "preview": [],
            "model": {
                "available": False,
                "status": "skipped_no_data",
                "anchor_count": 0,
                "class_count": 0,
            },
            "thresholds": {
                "high": constants.HIGH_CONFIDENCE,
                "medium": constants.MEDIUM_CONFIDENCE,
            },
            "strategy": "fuzzy_match",
        }

    profiles = {h: parsing_helpers.profile_column([(r.get(h, "") or "") for r in sample_rows]) for h in headers}

    header_scores = {h: {f: scoring_helpers.header_score(f, h) for f in constants.TARGET_FIELDS} for h in headers}
    model_probs, model_meta = model_helpers.maybe_model_probs(profiles, header_scores)
    model_available = bool(model_meta.get("available", False))

    blended: dict[str, dict[str, float]] = {}
    for h in headers:
        blended[h] = {}
        profile = profiles[h]
        for f in constants.TARGET_FIELDS:
            profile_component = scoring_helpers.profile_score(f, profile)
            model_component = model_probs[h][f]
            header_component = header_scores[h][f]
            header_w, profile_w, model_w = scoring_helpers.adaptive_blend_weights(
                header_component,
                profile_component,
                model_component,
                model_available=model_available,
            )
            blended[h][f] = header_w * header_component + profile_w * profile_component + model_w * model_component

    candidates: list[tuple[float, str, str]] = []
    for h in headers:
        for f in constants.TARGET_FIELDS:
            candidates.append((blended[h][f], f, h))
    candidates.sort(reverse=True)

    mapping: dict[str, str] = {}
    confidence: dict[str, float] = {}
    used_headers: set[str] = set()

    for score, field, header in candidates:
        if field in mapping or header in used_headers:
            continue
        if score < constants.MEDIUM_CONFIDENCE:
            continue
        mapping[field] = header
        confidence[field] = round(score, 3)
        used_headers.add(header)

    for field in constants.REQUIRED_FIELDS:
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
                    "high": constants.HIGH_CONFIDENCE,
                    "medium": constants.MEDIUM_CONFIDENCE,
                },
                "strategy": "fuzzy_match",
                "model": model_meta,
            }
        best_h = max(available_headers, key=lambda h: blended[h][field])
        mapping[field] = best_h
        confidence[field] = round(blended[best_h][field], 3)
        used_headers.add(best_h)

    scoring_helpers.attach_date_fallback(mapping, headers, {h: blended[h]["date"] for h in headers})

    alternatives: dict[str, list[mapper_types.CsvAlternative]] = {}
    for field in constants.TARGET_FIELDS:
        ranked = sorted(headers, key=lambda h: blended[h][field], reverse=True)[:3]
        alternatives[field] = [{"header": h, "score": round(blended[h][field], 3)} for h in ranked]

    low_required = any(confidence.get(f, 0.0) < constants.MEDIUM_CONFIDENCE for f in constants.REQUIRED_FIELDS)
    low_any = any(v < constants.HIGH_CONFIDENCE for k, v in confidence.items() if not k.startswith("_"))

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
            "high": constants.HIGH_CONFIDENCE,
            "medium": constants.MEDIUM_CONFIDENCE,
        },
        "strategy": "fuzzy_match",
    }
