# PyTorch Grokking Experiment Report

## Overview
- **Experiment ID**: `exp_1785360132042_p113`
- **ML Core Engine**: `pytorch_core`
- **Artifact Source**: `REAL_PYTORCH_RUN`
- **Status**: **COMPLETED**
- **Status Classifier**: `GROKKING_CONFIRMED`
- **Steps Completed**: `40000 / 40000`

## Hyperparameters & Configuration
- **Dataset Prime (p)**: `113` (`target = (a + b) mod 113`)
- **Model Type**: `transformer_1layer`
- **Architecture**: `transformer_1layer`
- **Architecture Version**: `canonical_v1`
- **Vocab Size**: `114`
- **d_model**: `128`
- **hidden_size**: `None`
- **d_mlp**: `512`
- **n_heads**: `4`
- **n_layers**: `1`
- **Context Length**: `3`
- **Tokenization Spec**: `[a, b, EQUALS] with EQUALS token id p and vocab_size p + 1`
- **Prediction Position**: `last`
- **Dropout**: `0.0`
- **Normalization Type**: `none`
- **Activation**: `relu`
- **Attention Mask**: `causal`
- **Train Split**: `0.3`
- **Seed**: `42`
- **Optimizer**: `AdamW (lr=0.001, weight_decay=1.0)`
- **Log Interval**: `100`
- **Full Batch**: `True`

## Final Training Metrics
- **Train Accuracy**: `1.0000` (100.00%)
- **Validation Accuracy**: `1.0000` (100.00%)
- **Train Loss**: `0.000002`
- **Validation Loss**: `0.000003`
- **Weight Norm ($||W||_2$)**: `39.2660`

## Grokking Event Milestones
- **Memorization Step (Train Acc >= 0.98)**: `200`
- **Candidate Grokking Step (Val Acc >= 0.985)**: `25600`
- **Plateau Step (10 consecutive checks >= 0.985)**: `26500`

## Saved PyTorch Checkpoints
| Checkpoint Name | Format | Step | Role | Replayed Train Acc | Replayed Val Acc | SHA-256 |
|---|---|---|---|---|---|---|
| `init_model_state.pt` | `pt` | 0 | `INIT_BEFORE_TRAINING` | 0.0094 | 0.0094 | `7d75619e243f4c67...` |
| `memorization_model_state.pt` | `pt` | 200 | `MEMORIZATION` | 0.9984 | 0.0004 | `8ccfd8a8f05c7956...` |
| `threshold_98_5_model_state.pt` | `pt` | 25600 | `GROKKING_CANDIDATE` | 1.0000 | 0.9978 | `56b76427bb6dd469...` |
| `plateau_model_state.pt` | `pt` | 26500 | `PLATEAU` | 1.0000 | 1.0000 | `ee84d150725923e7...` |
| `final_model_state.pt` | `pt` | 40000 | `FINAL_MODEL_STATE` | 1.0000 | 1.0000 | `c68fb6ced6da0eb1...` |

## Grokking Claim Authenticity Audit
- **authenticity_status**: `PASS`
- **baseline_check**: `PASS`
- **manifest_check**: `PASS`
- **timeseries_check**: `PASS`
- **checkpoint_replay_check**: `PASS`
- **no_fake_metrics_check**: `PASS`
- **architecture_contract_check**: `PASS`
- **config_manifest_checkpoint_parity**: `PASS`
- **tokenization_round_trip_check**: `PASS`
- **replay_max_abs_diff**: `0.0`
- **has_layernorm**: `False`
- **final_scientific_status**: `VERIFIED_SINGLE_RUN_GROKKING`

## Conclusion & Limitations
This PyTorch run serves as the reference benchmark to evaluate whether grokking (delayed generalization) occurs under standard float32 PyTorch training dynamics.
A single experiment run does not prove or disprove general grokking mechanisms across all hyperparameter regimes.
