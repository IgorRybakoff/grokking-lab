from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExperimentConfig:
    p: int = 113
    train_fraction: float = 0.30
    seed: int = 42
    d_model: int = 128
    n_heads: int = 4
    d_mlp: int = 512
    n_layers: int = 1
    context_length: int = 3
    activation: str = "relu"
    normalization_type: str = "none"
    dropout: float = 0.0
    causal_attention: bool = True
    learning_rate: float = 0.001
    weight_decay: float = 1.0
    max_steps: int = 40_000
    log_interval: int = 100
    full_batch: bool = True
    run_mode: str = "long_run"
    experiment_id: str = ""

    def validate(self) -> None:
        if self.p < 2:
            raise ValueError("p must be at least 2")
        if not 0.0 < self.train_fraction < 1.0:
            raise ValueError("train_fraction must be between 0 and 1")
        if self.d_model % self.n_heads:
            raise ValueError("d_model must be divisible by n_heads")
        if self.n_layers != 1:
            raise ValueError("public v0.1 implements exactly one transformer layer")
        if self.context_length != 3:
            raise ValueError("canonical_v1 uses context_length=3")
        if self.activation != "relu" or self.normalization_type != "none":
            raise ValueError("canonical_v1 requires ReLU and no normalization")
        if self.dropout != 0.0:
            raise ValueError("canonical_v1 requires dropout=0.0")
        if not self.full_batch:
            raise ValueError("public v0.1 supports full-batch training only")
        if self.max_steps < 1 or self.log_interval < 1:
            raise ValueError("max_steps and log_interval must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, path: str | Path) -> "ExperimentConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        config = cls(**data)
        config.validate()
        return config

