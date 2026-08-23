# Reproducibility

This repository separates four different levels of verification.

## 1. Artifact integrity (no training)

```bash
python scripts/verify_artifacts.py
```

This checks SHA-256 values, manifest gates, finite timeseries values, the exact 0..40,000/100 step sequence, and recomputes the recorded event milestones.

## 2. Checkpoint replay (no retraining)

```bash
python scripts/replay_checkpoint.py --checkpoint memorization_model_state.pt
python scripts/replay_checkpoint.py --checkpoint final_model_state.pt
```

Replay reconstructs the dataset and split, loads weights with `torch.load(..., weights_only=True)`, performs a new forward pass, and compares measured losses and accuracies with the frozen replay report.

## 3. PyTorch smoke training

```bash
python scripts/run_smoke.py --output runs/smoke
```

This executes a real forward pass, backward pass, AdamW update, and artifact write. It asserts that parameters changed. It does **not** attempt to demonstrate grokking.

## 4. Optional long-run reproduction

```bash
python scripts/run_experiment.py \
  --config configs/p113_seed42_40k.json \
  --output runs/p113_seed42_40k
```

This command requests 40,000 full-batch optimizer steps and can take substantial CPU time. The timing and exact transition step may vary across environments. A successful independent rerun should be reported separately from the frozen 2026 evidence rather than overwriting it.

## Original environment and provenance boundary

The frozen manifest reports:

- Python 3.14.3;
- PyTorch 2.13.0;
- NumPy 2.5.1;
- CPU;
- `artifact_source=REAL_PYTORCH_RUN`;
- `fallback_used=false`;
- `simulated_metrics=false`;
- `llm_generated_metrics=false`.

The original source-code hash was not preserved. Public v0.1 therefore does not claim byte identity with the historical training script. It publishes a cleaned implementation of the recorded architecture contract and requires functional checkpoint replay as the compatibility gate.

> LLM never creates metrics; LLM only interprets measured evidence.

