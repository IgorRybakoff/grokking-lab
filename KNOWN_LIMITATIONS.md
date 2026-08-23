# Known limitations

Public v0.1 intentionally makes a narrow claim: one frozen PyTorch run on modular addition with `p=113` and seed 42 passed the documented run-level grokking policy.

- This release publishes one seed. It does not establish universality across seeds, tasks, architectures, optimizers, or scales.
- Modular addition is a complete synthetic table, not a proxy for real-world language or multimodal generalization.
- The model is a compact one-layer, full-batch Transformer with no normalization and no dropout.
- Milestones at steps 200, 25,600, and 26,500 depend on thresholds and the 100-step logging cadence.
- `GROKKING_CONFIRMED` is a deterministic status under this repository's event policy, not a claim of human-like understanding or a universal scientific definition.
- The frozen run demonstrates a behavioral transition; it does not identify the causal circuit or mechanistic reason for that transition.
- CI runs a two-step PyTorch smoke test and checkpoint replay. It does not rerun 40,000 training steps.
- Identical seeds do not guarantee bitwise-identical training across PyTorch versions, hardware, BLAS implementations, CUDA, or MPS.
- The original manifest records Python 3.14.3, PyTorch 2.13.0, NumPy 2.5.1, and CPU execution. Public CI validates replay on its current pinned-compatible CPU environment rather than claiming an identical machine image.
- The original run did not preserve a source-code hash or explicit split-index file. The public implementation follows the frozen architecture contract and deterministic split rule, and its functional equivalence is checked by checkpoint replay.
- The original config incorrectly labels the 40,000-step run as `mode=smoke_test`. The byte-preserved file is not rewritten; the public execution recipe correctly uses `run_mode=long_run`.
- Checksums detect changes to the published package. They are integrity controls, not independent third-party attestation.

