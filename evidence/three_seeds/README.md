# Three-seed research evidence

This directory publishes the original full historical experiment archives for seeds 43 and 44, plus the supplied validation plot. The frozen seed-42 package remains in [artifacts/p113_seed42_40k](../../artifacts/p113_seed42_40k).

| Seed | Experiment ID | Memorization (train >= 0.98) | Candidate (validation >= 0.985) | Plateau | Final train / validation |
|---|---|---:|---:|---:|---|
| 42 | exp_1785360132042_p113 | 200 | 25600 | 26500 | 1.0 / 1.0 |
| 43 | exp_1785406284582_p113 | 302 | 32300 | 33200 | 1.0 / 1.0 |
| 44 | exp_p113_seed44_research_v04 | 416 | 23000 | 23900 | 1.0 / 1.0 |

- [Seed 43 full archive](exp_1785406284582_p113_FULL.zip)
- [Seed 44 full archive](exp_p113_seed44_research_v04_FULL.zip)
- [Supplied validation plot](three_seed_validation.png)

## Verification performed on 2026-10-04

Both ZIP CRC checks passed. Each seed-43/44 timeseries has 403 unique rows: 401 regular points from step 0 to 40000 every 100 steps, plus the two adjacent memorization-boundary records. Numeric accuracy/loss values are finite and timestamps are ordered. Recomputed milestones match the table. All five checkpoint SHA-256 values per run match the preserved replay report. Recomputed differences between recorded checkpoint replay accuracy/loss and matching timeseries rows are exactly 0.0.

The preserved replay reports record PASS and replay_max_abs_diff = 0.0. This publication check compared those reports with the measured timeseries and checkpoint bytes; it did not perform a new independent PyTorch forward pass or retrain a model.

## Measurement and provenance limits

Memorization for seed 42 is recorded at the historical 100-step logging resolution; seeds 43 and 44 check memorization every optimizer step. Generalization is checked every 100 steps. Plateau means 10 consecutive checks at or above 0.985, spanning 900 steps from the first to the tenth check.

Seed 44 preserves dataset_split.json, environment_lock.json and source_hash_manifest.json. Its source manifest records unavailable Git dirty-state detection; do not equate its hash record with a verified clean Git checkout. Earlier runs have weaker historical source/split provenance.

The supplied PNG is a presentation asset. Scientific values must be checked against training_timeseries.json in the archives.

These three runs support delayed generalization in the documented modular-addition configuration. They do not establish universal grokking or isolate the causal effect of initialization from changes in the dataset split.

The archives are preserved byte-for-byte, including historical packaging entries. SHA256SUMS records the published byte hashes.
