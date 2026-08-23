from __future__ import annotations

import torch
from torch import nn

from .config import ExperimentConfig


class CanonicalTransformer(nn.Module):
    """The one-layer, no-normalization Transformer used by the frozen run."""

    def __init__(self, config: ExperimentConfig):
        super().__init__()
        config.validate()
        self.config = config
        self.token_embedding = nn.Embedding(config.p + 1, config.d_model)
        self.pos_embedding = nn.Embedding(config.context_length, config.d_model)
        self.attn = nn.MultiheadAttention(
            embed_dim=config.d_model,
            num_heads=config.n_heads,
            dropout=config.dropout,
            batch_first=True,
        )
        self.mlp = nn.Sequential(
            nn.Linear(config.d_model, config.d_mlp),
            nn.ReLU(),
            nn.Linear(config.d_mlp, config.d_model),
        )
        self.unembed = nn.Linear(config.d_model, config.p)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        if tokens.ndim != 2 or tokens.shape[1] != self.config.context_length:
            raise ValueError("tokens must have shape [batch, context_length]")
        positions = torch.arange(tokens.shape[1], device=tokens.device)
        x = self.token_embedding(tokens) + self.pos_embedding(positions)[None, :, :]
        mask = torch.triu(
            torch.ones(tokens.shape[1], tokens.shape[1], dtype=torch.bool, device=tokens.device),
            diagonal=1,
        )
        attended, _ = self.attn(x, x, x, attn_mask=mask, need_weights=False)
        x = x + attended
        x = x + self.mlp(x)
        return self.unembed(x[:, -1, :])

