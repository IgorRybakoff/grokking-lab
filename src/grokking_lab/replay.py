from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from .config import ExperimentConfig
from .data import make_modular_addition_data
from .metrics import evaluate, weight_norm
from .model import CanonicalTransformer


def canonical_config_from_artifact(artifact_dir: str | Path) -> ExperimentConfig:
    original = json.loads((Path(artifact_dir) / "config.json").read_text(encoding="utf-8"))
    return ExperimentConfig(
        p=int(original["p"]),
        train_fraction=float(original["train_split"]),
        seed=int(original["seed"]),
        d_model=int(original["d_model"]),
        n_heads=int(original["n_heads"]),
        d_mlp=int(original["d_mlp"]),
        n_layers=int(original["n_layers"]),
        context_length=int(original["context_length"]),
        activation=str(original["activation"]),
        normalization_type=str(original["normalization_type"]),
        dropout=float(original["dropout"]),
        causal_attention=bool(original["causal_attention"]),
        learning_rate=float(original["learning_rate"]),
        weight_decay=float(original["weight_decay"]),
        max_steps=int(original["max_steps"]),
        log_interval=int(original["log_interval"]),
        full_batch=bool(original["full_batch"]),
        run_mode="frozen_replay",
        experiment_id=str(original["experiment_id"]),
    )


def replay_checkpoint(
    artifact_dir: str | Path,
    checkpoint_name: str = "final_model_state.pt",
    device: str = "cpu",
) -> dict[str, Any]:
    root = Path(artifact_dir)
    config = canonical_config_from_artifact(root)
    data = make_modular_addition_data(config.p, config.train_fraction, config.seed, device=device)
    model = CanonicalTransformer(config).to(device)
    state = torch.load(root / "checkpoints" / checkpoint_name, map_location=device, weights_only=True)
    model.load_state_dict(state, strict=True)

    train = evaluate(model, data.train_tokens, data.train_targets)
    validation = evaluate(model, data.validation_tokens, data.validation_targets)
    result = {
        "checkpoint_name": checkpoint_name,
        "train_accuracy": train["accuracy"],
        "validation_accuracy": validation["accuracy"],
        "train_loss": train["loss"],
        "validation_loss": validation["loss"],
        "weight_norm": weight_norm(model),
        "split_sha256": data.split_sha256,
    }

    report = json.loads((root / "checkpoint_replay_report.json").read_text(encoding="utf-8"))
    expected = next(item for item in report["checkpoints"] if item["checkpoint_name"] == checkpoint_name)
    result["expected"] = {
        "train_accuracy": expected["replay_train_accuracy"],
        "validation_accuracy": expected["replay_val_accuracy"],
        "train_loss": expected["replay_train_loss"],
        "validation_loss": expected["replay_val_loss"],
    }
    accuracy_match = (
        result["train_accuracy"] == result["expected"]["train_accuracy"]
        and result["validation_accuracy"] == result["expected"]["validation_accuracy"]
    )
    loss_match = all(
        abs(result[key] - result["expected"][key]) <= max(1e-5, abs(result["expected"][key]) * 1e-4)
        for key in ("train_loss", "validation_loss")
    )
    result["status"] = "PASS" if accuracy_match and loss_match else "FAIL"
    return result

