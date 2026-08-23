import torch

from grokking_lab.config import ExperimentConfig
from grokking_lab.model import CanonicalTransformer


def test_forward_shape_and_state_dict_contract():
    model = CanonicalTransformer(ExperimentConfig())
    logits = model(torch.tensor([[1, 2, 113], [112, 1, 113]]))
    assert logits.shape == (2, 113)
    assert list(model.state_dict()) == [
        "token_embedding.weight",
        "pos_embedding.weight",
        "attn.in_proj_weight",
        "attn.in_proj_bias",
        "attn.out_proj.weight",
        "attn.out_proj.bias",
        "mlp.0.weight",
        "mlp.0.bias",
        "mlp.2.weight",
        "mlp.2.bias",
        "unembed.weight",
        "unembed.bias",
    ]

