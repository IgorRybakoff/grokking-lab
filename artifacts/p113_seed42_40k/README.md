# Frozen evidence: exp_1785360132042_p113

This directory contains byte-preserved evidence from the completed seed 42 PyTorch run created on 29 July 2026.

## Classification

- `config.json`, `experiment_manifest.json`, `training_timeseries.json`, `grokking_event_detection.json`, `validation_diagnostics.json`, `checkpoint_replay_report.json`, `report.md`, and `checkpoints/*.pt`: `original_run`.
- `plots/grokking_curve.png`: `derived_from_measured_data`.
- `artifact_index.json`, `README.md`, and `SHA256SUMS`: `publication_metadata`.

The original files are intentionally not normalized. In particular, the historical `config.json` contains the known incorrect label `mode=smoke_test`; see [`../../KNOWN_LIMITATIONS.md`](../../KNOWN_LIMITATIONS.md).

Use `python scripts/verify_artifacts.py` from the repository root to validate this evidence package.

