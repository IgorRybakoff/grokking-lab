from __future__ import annotations

import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from .config import ExperimentConfig
from .data import make_modular_addition_data
from .metrics import evaluate, weight_norm
from .model import CanonicalTransformer


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_training(config: ExperimentConfig, output_dir: str | Path) -> dict[str, Any]:
    config.validate()
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(config.seed)
    np.random.seed(config.seed)
    torch.use_deterministic_algorithms(True)

    data = make_modular_addition_data(config.p, config.train_fraction, config.seed)
    model = CanonicalTransformer(config)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay
    )
    initial_parameter_vector = torch.nn.utils.parameters_to_vector(model.parameters()).detach().clone()
    started = time.monotonic()
    rows = []

    for step in range(config.max_steps + 1):
        if step > 0:
            model.train()
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(data.train_tokens), data.train_targets)
            loss.backward()
            optimizer.step()
        if step % config.log_interval == 0 or step == config.max_steps:
            train = evaluate(model, data.train_tokens, data.train_targets)
            validation = evaluate(model, data.validation_tokens, data.validation_targets)
            rows.append({
                "step": step,
                "train_loss": train["loss"],
                "val_loss": validation["loss"],
                "train_acc": train["accuracy"],
                "val_acc": validation["accuracy"],
                "weight_norm": weight_norm(model),
            })

    final_parameter_vector = torch.nn.utils.parameters_to_vector(model.parameters()).detach()
    parameters_changed = not torch.equal(initial_parameter_vector, final_parameter_vector)
    manifest = {
        "experiment_id": config.experiment_id or output.name,
        "engine_type": "pytorch_core",
        "artifact_source": "REAL_PYTORCH_RUN",
        "fallback_used": False,
        "simulated_metrics": False,
        "llm_generated_metrics": False,
        "status": "COMPLETED",
        "exit_code": 0,
        "run_mode": config.run_mode,
        "seed": config.seed,
        "dataset_p": config.p,
        "train_fraction": config.train_fraction,
        "split_sha256": data.split_sha256,
        "parameters_changed": parameters_changed,
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "device": "cpu",
        "duration_ms": int((time.monotonic() - started) * 1000),
        "completed_at": _utc_now(),
    }
    (output / "config.json").write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")
    (output / "training_timeseries.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    (output / "experiment_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    torch.save(model.state_dict(), output / "final_model_state.pt")
    if not parameters_changed:
        raise RuntimeError("optimizer did not change model parameters")
    return manifest

