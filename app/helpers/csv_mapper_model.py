"""Optional ML model helpers for transaction CSV mapper."""

from __future__ import annotations

from app.helpers.csv_mapper_constants import MIN_MODEL_ANCHORS, MIN_MODEL_CLASSES, TARGET_FIELDS
from app.helpers.csv_mapper_types import ColumnProfile, CsvModelMeta


def maybe_model_probs(
    profiles: dict[str, ColumnProfile], header_scores: dict[str, dict[str, float]]
) -> tuple[dict[str, dict[str, float]], CsvModelMeta]:
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

    anchor_features: list[list[float]] = []
    anchor_labels: list[str] = []

    def profile_vector(profile: ColumnProfile) -> list[float]:
        return [
            profile.null_rate,
            profile.date_rate,
            profile.numeric_rate,
            profile.bool_rate,
            profile.neg_rate,
            profile.median_abs,
            profile.mean_len,
            profile.unique_ratio,
            profile.direction_token_rate,
        ]

    for header, scores_for_header in header_scores.items():
        top_field = max(scores_for_header, key=lambda field_name: scores_for_header[field_name])
        score = scores_for_header[top_field]
        if score >= 0.92:
            anchor_features.append(profile_vector(profiles[header]))
            anchor_labels.append(top_field)

    anchor_count = len(anchor_features)
    class_count = len(set(anchor_labels))

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
        model.fit(anchor_features, anchor_labels)
        probabilities_by_header: dict[str, dict[str, float]] = {}
        classes = list(model.classes_)
        for header, profile in profiles.items():
            probabilities = model.predict_proba([profile_vector(profile)])[0]
            class_probabilities = {f: 0.0 for f in TARGET_FIELDS}
            for idx, cls in enumerate(classes):
                class_probabilities[str(cls)] = float(probabilities[idx])
            probabilities_by_header[header] = class_probabilities
        return (
            probabilities_by_header,
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
