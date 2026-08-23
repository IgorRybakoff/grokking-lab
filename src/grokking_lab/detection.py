from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def detect_events(
    rows: Iterable[dict[str, Any]],
    memorization_threshold: float = 0.98,
    generalization_threshold: float = 0.985,
    stability_checks: int = 10,
) -> dict[str, int | str | None]:
    memorization_step = None
    candidate_step = None
    plateau_step = None
    consecutive = 0

    for row in sorted(rows, key=lambda item: int(item["step"])):
        train_accuracy = float(row.get("train_accuracy", row.get("train_acc", 0.0)))
        validation_accuracy = float(row.get("val_accuracy", row.get("val_acc", 0.0)))
        step = int(row["step"])

        if memorization_step is None and train_accuracy >= memorization_threshold:
            memorization_step = step
        if validation_accuracy >= generalization_threshold:
            consecutive += 1
            if candidate_step is None:
                candidate_step = step
            if plateau_step is None and consecutive >= stability_checks:
                plateau_step = step
        else:
            consecutive = 0

    status = "GROKKING_CONFIRMED" if plateau_step is not None else (
        "GROKKING_CANDIDATE" if candidate_step is not None else (
            "MEMORIZATION_ONLY" if memorization_step is not None else "COMPLETED_NO_MEMORIZATION"
        )
    )
    return {
        "memorization_step": memorization_step,
        "grokking_candidate_step": candidate_step,
        "plateau_step": plateau_step,
        "status_classifier": status,
    }

