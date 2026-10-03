# Grokking Lab

[![tests](https://github.com/IgorRybakoff/grokking-lab/actions/workflows/tests.yml/badge.svg)](https://github.com/IgorRybakoff/grokking-lab/actions/workflows/tests.yml)

**Reproducible ML experiment audit and evidence packaging, built on a real Grokking research corpus.**

> **LLM never creates metrics; LLM only interprets measured evidence.**

Grokking Lab started as an experimental research package for delayed generalization in modular addition. MVP v0.1 adds a narrow product layer: upload a frozen experiment/evidence ZIP, verify configuration/environment/integrity, replay supported checkpoints, receive a deterministic `VERIFIED` / `FAILED` / `INCOMPLETE` verdict, and download a portable evidence package.

**Status:** MVP v0.1 — experimental  
**Language:** Python >= 3.10 / PyTorch  
**License:** Apache-2.0

## Product MVP: one-screen experiment audit

Install the web extra and launch locally:

```bash
python -m pip install -e ".[web]"
grokking-lab serve
```

Open `http://127.0.0.1:8000` and either:

1. press **TRY CANONICAL DEMO** to audit the frozen seed-42 run; or
2. upload one Grokking Lab evidence ZIP and press **VERIFY EXPERIMENT**.

The product returns a machine-readable audit with three intentionally strict outcomes:

- `VERIFIED` — all required evidence checks and supported checkpoint replay passed;
- `FAILED` — available evidence contradicts the recorded claim or integrity/replay check;
- `INCOMPLETE` — evidence is insufficient to establish verification.

The web MVP never executes arbitrary code from uploaded archives. Unknown repositories require a future isolated runner/container; this boundary is deliberate.

CLI equivalents remain available:

```bash
grokking-lab audit --artifact-dir artifacts/p113_seed42_40k
grokking-lab replay --artifact-dir artifacts/p113_seed42_40k
grokking-lab export --artifact-dir artifacts/p113_seed42_40k --output evidence.zip
grokking-lab compare run_a run_b
```

See [`MVP_V0_1.md`](MVP_V0_1.md) for scope and acceptance gates.

## Research question

Can a compact Transformer trained on only 30% of the complete modular-addition table first memorize its training subset and later generalize to the held-out 70% after a long delay?

## What this repository establishes

- a real PyTorch training path performs forward, backward, and AdamW updates;
- the frozen seed 42 run contains 401 measured records from step 0 through 40,000;
- five original PyTorch state-dict checkpoints have verified SHA-256 values;
- checkpoint replay performs new forward passes and matches recorded metrics;
- deterministic threshold checks classify this run as `GROKKING_CONFIRMED`.

It does **not** claim that grokking is universal across seeds, architectures, tasks, optimizers, or scales.

## Experimental setup

| Component | Frozen configuration |
|---|---|
| Task | `(a + b) mod 113` |
| Input | `[a, b, EQUALS]`, context length 3 |
| Split | 30% train / 70% validation |
| Seed | 42 |
| Model | One-layer Transformer, last-token prediction |
| Width | `d_model=128`, 4 heads, `d_mlp=512` |
| Block | Attention residual + ReLU MLP residual |
| Normalization / dropout | None / 0.0 |
| Optimizer | Full-batch AdamW |
| Learning rate / weight decay | 0.001 / 1.0 |
| Training | 40,000 optimizer steps |

## Measured result

| Metric | Frozen value |
|---|---:|
| Final train accuracy | 1.000000 |
| Final validation accuracy | 1.000000 |
| Memorization | step 200 |
| Generalization candidate | step 25,600 |
| Stable plateau | step 26,500 |
| Final train loss | 1.86140596e-6 |
| Final validation loss | 2.59322110e-6 |
| Final weight norm | 39.26596859 |
| Run-level classification | `GROKKING_CONFIRMED` |

![Measured train and validation accuracy](artifacts/p113_seed42_40k/plots/grokking_curve.png)

The plot is generated directly from the frozen `training_timeseries.json` without smoothing or synthetic points.

## Quick verification

```bash
git clone https://github.com/IgorRybakoff/grokking-lab.git
cd grokking-lab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,web]"
```

### 1. Verify the frozen evidence

```bash
python scripts/verify_artifacts.py
```

Expected high-level result:

```text
status: PASS
experiment_id: exp_1785360132042_p113
timeseries_rows: 401
memorization_step: 200
grokking_candidate_step: 25600
plateau_step: 26500
```

### 2. Replay measured checkpoints

```bash
python scripts/replay_checkpoint.py --checkpoint memorization_model_state.pt
python scripts/replay_checkpoint.py --checkpoint final_model_state.pt
```

Replay loads state dicts with `weights_only=True`, reconstructs the original deterministic split, runs new forward passes, and compares the results with the frozen replay report.

### 3. Run a real PyTorch smoke test

```bash
python scripts/run_smoke.py --output runs/smoke
```

The smoke test performs two full-batch optimizer steps and proves that parameters changed. It does not attempt to reproduce grokking.

### 4. Optional 40k reproduction

```bash
python scripts/run_experiment.py \
  --config configs/p113_seed42_40k.json \
  --output runs/p113_seed42_40k
```

The long run is deliberately excluded from CI.

## Evidence map

| Evidence | Purpose |
|---|---|
| [`config.json`](artifacts/p113_seed42_40k/config.json) | Byte-preserved historical configuration |
| [`experiment_manifest.json`](artifacts/p113_seed42_40k/experiment_manifest.json) | Engine, environment, provenance, completion, checkpoint registry |
| [`training_timeseries.json`](artifacts/p113_seed42_40k/training_timeseries.json) | Measured losses, accuracies, and weight norms |
| [`grokking_event_detection.json`](artifacts/p113_seed42_40k/grokking_event_detection.json) | Recorded milestones and run-level status |
| [`checkpoint_replay_report.json`](artifacts/p113_seed42_40k/checkpoint_replay_report.json) | New-forward-pass replay results |
| [`SHA256SUMS`](artifacts/p113_seed42_40k/SHA256SUMS) | Published package integrity |
| [`artifact_index.json`](artifacts/p113_seed42_40k/artifact_index.json) | Original vs derived vs publication metadata |

The frozen manifest records:

```text
engine_type = pytorch_core
artifact_source = REAL_PYTORCH_RUN
fallback_used = false
simulated_metrics = false
llm_generated_metrics = false
```

## Repository layout

- `src/grokking_lab/` — minimal public training, model, provenance, replay, audit, evidence export, and web product code;
- `configs/` — CI smoke and optional long-run execution recipes;
- `experiments/` — human-readable experimental protocol;
- `artifacts/` — frozen measured evidence and selected checkpoints;
- `scripts/` — verification, replay, plotting, smoke, and long-run entry points;
- `tests/` — task, architecture, integrity, smoke, replay, audit, and web safety checks.

## Reproducibility boundary

The historical run did not preserve a source-code hash or explicit split-index file. Public v0.1 therefore does not claim byte identity with the original internal training script. The public implementation follows the recorded architecture contract, matches the checkpoint state-dict structure exactly, reconstructs the deterministic split, and uses functional checkpoint replay as its compatibility gate.

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) and [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md).

## Citation and license

Citation metadata is available in [`CITATION.cff`](CITATION.cff). The public code is licensed under Apache-2.0. Frozen artifacts are supplied for research verification of the documented experiment.
