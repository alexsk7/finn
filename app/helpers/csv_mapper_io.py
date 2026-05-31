"""CSV delimiter detection helpers for transaction CSV mapper."""

from __future__ import annotations

import csv


def sniff_delimiter(lines: list[str]) -> str:
    sample = "\n".join(lines[:8])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        return dialect.delimiter
    except Exception:
        return best_delimiter_fallback(lines[:8])


def best_delimiter_fallback(lines: list[str]) -> str:
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
