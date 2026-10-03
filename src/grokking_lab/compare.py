from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value}
    flattened: dict[str, Any] = {}
    for key in sorted(value):
        path = f"{prefix}.{key}" if prefix else key
        child = value[key]
        if isinstance(child, dict):
            flattened.update(_flatten(child, path))
        else:
            flattened[path] = child
    return flattened


def _final_checkpoint_summary(root: Path) -> dict[str, Any]:
    report = _load_object(root / "checkpoint_replay_report.json")
    checkpoints = report.get("checkpoints")
    if not isinstance(checkpoints, list) or not checkpoints:
        return {}

    final = next(
        (item for item in checkpoints if item.get("checkpoint_semantic_role") == "FINAL_MODEL_STATE"),
        checkpoints[-1],
    )
    return {
        "checkpoint_name": final.get("checkpoint_name"),
        "checkpoint_step": final.get("checkpoint_step"),
        "train_accuracy": final.get("replay_train_accuracy"),
        "validation_accuracy": final.get("replay_val_accuracy"),
        "train_loss": final.get("replay_train_loss"),
        "validation_loss": final.get("replay_val_loss"),
        "replay_status": final.get("replay_status"),
    }


def compare_runs(artifact_dirs: list[str | Path]) -> dict[str, Any]:
    if not 2 <= len(artifact_dirs) <= 5:
        raise ValueError("compare requires between 2 and 5 runs")

    runs: list[dict[str, Any]] = []
    flat_configs: list[dict[str, Any]] = []
    for index, artifact_dir in enumerate(artifact_dirs, start=1):
        root = Path(artifact_dir)
        config = _load_object(root / "config.json")
        manifest = _load_object(root / "experiment_manifest.json")
        run_label = f"run_{index}"
        runs.append(
            {
                "label": run_label,
                "experiment_id": manifest.get("experiment_id", root.name),
                "artifact_dir": str(root),
                "final": _final_checkpoint_summary(root),
            }
        )
        flat_configs.append(_flatten(config))

    keys = sorted(set().union(*(config.keys() for config in flat_configs)))
    varying_config: dict[str, dict[str, Any]] = {}
    for key in keys:
        values = [config.get(key) for config in flat_configs]
        comparable = [json.dumps(value, sort_keys=True, default=str) for value in values]
        if len(set(comparable)) > 1:
            varying_config[key] = {runs[i]["label"]: values[i] for i in range(len(runs))}

    return {
        "schema_version": "grokkinglab.compare.v0.1",
        "status": "PASS",
        "run_count": len(runs),
        "runs": runs,
        "varying_config": varying_config,
    }
