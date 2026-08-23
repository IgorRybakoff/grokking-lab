# Experiment protocol: p113 / seed 42 / 40k

## Research question

Can a compact Transformer trained on 30% of the complete modular-addition table first memorize the training subset and then generalize to the held-out 70% after a long delay?

## Task

- Inputs: `[a, b, EQUALS]`, where `0 <= a,b < 113` and `EQUALS=113`.
- Target: `(a + b) mod 113`.
- Complete table: 12,769 examples.
- Training subset: 3,830 examples (30%).
- Validation subset: 8,939 examples (70%).
- Split: `numpy.random.RandomState(42).permutation(12769)`.
- Public split SHA-256: `447b85aa50b551871fa7e136c40ded3a0925734e6200e909dea17455c57662bd`.

## Model and optimization

One Transformer layer, learned token and positional embeddings, four attention heads, two residual connections, a 128→512→128 ReLU MLP, no normalization, no dropout, and last-token prediction. Training used full-batch AdamW with learning rate `0.001` and weight decay `1.0` for 40,000 optimizer steps.

## Event policy

- Memorization: first logged point with train accuracy >= 0.98.
- Candidate: first logged point with validation accuracy >= 0.985.
- Plateau: ten consecutive logged validation checks >= 0.985.
- Metrics were logged every 100 steps in the frozen run.

The policy classified the run as `GROKKING_CONFIRMED`. This is a run-level classification under the stated thresholds, not a universal definition of grokking.

## Evidence

The byte-preserved original artifacts are in [`../../artifacts/p113_seed42_40k/`](../../artifacts/p113_seed42_40k/). The original run did not preserve a source-code hash or split-index file; this is explicitly treated as a limitation.

