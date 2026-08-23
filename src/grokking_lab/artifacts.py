from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .detection import detect_events


REQUIRED_EVIDENCE = (
    "config.json",
    "experiment_manifest.json",
    "training_timeseries.json",
    "grokking_event_detection.json",
    "validation_diagnostics.json",
    "checkpoint_replay_report.json",
    "report.md",
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_sha256sums(path: str | Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split(maxsplit=1)
        entries[relative.lstrip("* ")] = digest
    return entries


def verify_artifact_directory(artifact_dir: str | Path) -> dict[str, Any]:
    root = Path(artifact_dir)
    missing = [name for name in REQUIRED_EVIDENCE if not (root / name).is_file()]
    if missing:
        raise ValueError(f"missing required evidence: {missing}")

    manifest = load_json(root / "experiment_manifest.json")
    forbidden = {
        "fallback_used": False,
        "simulated_metrics": False,
        "llm_generated_metrics": False,
    }
    if manifest.get("engine_type") != "pytorch_core":
        raise ValueError("manifest engine_type is not pytorch_core")
    if manifest.get("artifact_source") != "REAL_PYTORCH_RUN":
        raise ValueError("manifest artifact_source is not REAL_PYTORCH_RUN")
    for key, expected in forbidden.items():
        if manifest.get(key) is not expected:
            raise ValueError(f"manifest gate failed: {key}")
    if manifest.get("status") != "COMPLETED" or manifest.get("exit_code") != 0:
        raise ValueError("experiment did not complete successfully")

    timeseries = load_json(root / "training_timeseries.json")
    if not isinstance(timeseries, list) or not timeseries:
        raise ValueError("training_timeseries.json is empty")
    steps = [int(row["step"]) for row in timeseries]
    if steps != list(range(0, 40_001, 100)):
        raise ValueError("timeseries does not contain the frozen 0..40000/100 sequence")
    numeric_keys = ("train_loss", "val_loss", "train_acc", "val_acc", "weight_norm")
    if any(not math.isfinite(float(row[key])) for row in timeseries for key in numeric_keys):
        raise ValueError("timeseries contains non-finite metrics")

    detected = detect_events(timeseries)
    recorded = load_json(root / "grokking_event_detection.json")
    for key in ("memorization_step", "grokking_candidate_step", "plateau_step", "status_classifier"):
        if detected[key] != recorded[key]:
            raise ValueError(f"event detection mismatch for {key}")

    sums = read_sha256sums(root / "SHA256SUMS")
    mismatches = []
    for relative, expected in sums.items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected:
            mismatches.append(relative)
    if mismatches:
        raise ValueError(f"checksum mismatch: {mismatches}")

    baseline = 1.0 / int(manifest["dataset_p"])
    return {
        "status": "PASS",
        "experiment_id": manifest["experiment_id"],
        "artifact_source": manifest["artifact_source"],
        "timeseries_rows": len(timeseries),
        "random_baseline": baseline,
        "events": detected,
        "checksums_verified": len(sums),
    }

