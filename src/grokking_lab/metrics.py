from __future__ import annotations

import math

import torch
from torch import nn


@torch.no_grad()
def evaluate(model: nn.Module, tokens: torch.Tensor, targets: torch.Tensor) -> dict[str, float]:
    model.eval()
    logits = model(tokens)
    loss = nn.functional.cross_entropy(logits, targets).item()
    accuracy = (logits.argmax(dim=-1) == targets).float().mean().item()
    return {"loss": loss, "accuracy": accuracy}


@torch.no_grad()
def weight_norm(model: nn.Module) -> float:
    return math.sqrt(sum(parameter.pow(2).sum().item() for parameter in model.parameters()))

