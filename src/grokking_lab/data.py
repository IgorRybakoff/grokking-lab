from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import torch


@dataclass(frozen=True)
class ModularAdditionData:
    train_tokens: torch.Tensor
    train_targets: torch.Tensor
    validation_tokens: torch.Tensor
    validation_targets: torch.Tensor
    train_indices: np.ndarray
    validation_indices: np.ndarray

    @property
    def split_sha256(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.train_indices.astype("<i8", copy=False).tobytes())
        digest.update(self.validation_indices.astype("<i8", copy=False).tobytes())
        return digest.hexdigest()


def make_modular_addition_data(
    p: int,
    train_fraction: float,
    seed: int,
    device: str | torch.device = "cpu",
) -> ModularAdditionData:
    """Build the original [a, b, EQUALS] task and deterministic split.

    RandomState deliberately matches the legacy ``np.random.seed`` followed by
    ``np.random.permutation`` used by the frozen experiment.
    """
    pairs = np.asarray([(a, b) for a in range(p) for b in range(p)], dtype=np.int64)
    targets = (pairs[:, 0] + pairs[:, 1]) % p
    indices = np.random.RandomState(seed).permutation(len(pairs))
    train_size = int(len(indices) * train_fraction)
    train_indices = indices[:train_size]
    validation_indices = indices[train_size:]

    def tensors(selected: np.ndarray) -> tuple[torch.Tensor, torch.Tensor]:
        selected_pairs = pairs[selected]
        equals = np.full((len(selected), 1), p, dtype=np.int64)
        tokens = np.concatenate([selected_pairs, equals], axis=1)
        return (
            torch.as_tensor(tokens, dtype=torch.long, device=device),
            torch.as_tensor(targets[selected], dtype=torch.long, device=device),
        )

    train_tokens, train_targets = tensors(train_indices)
    validation_tokens, validation_targets = tensors(validation_indices)
    return ModularAdditionData(
        train_tokens=train_tokens,
        train_targets=train_targets,
        validation_tokens=validation_tokens,
        validation_targets=validation_targets,
        train_indices=train_indices,
        validation_indices=validation_indices,
    )

