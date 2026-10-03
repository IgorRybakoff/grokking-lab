# Grokking Lab MVP v0.1 — Reproducible ML Experiment Audit

## Product boundary

Grokking Lab v0.1 is not a general MLOps platform. It is a narrow experiment-audit tool:

> Give it a frozen ML run and get a machine-readable verdict, replay evidence, comparison data, and a portable evidence package.

The core verdict must remain deterministic. LLMs may explain evidence or help map unfamiliar repositories into an adapter, but they must not decide VERIFIED / FAILED / INCOMPLETE.

## Must-have

1. Import or run one supported experiment.
2. Freeze configuration and environment evidence.
3. Preserve and hash checkpoints and critical artifacts.
4. Replay at least one checkpoint and compare recorded vs replayed metrics.
5. Return one of three audit outcomes: `VERIFIED`, `FAILED`, `INCOMPLETE`.
6. Compare 2–5 runs, focusing on config deltas and replayed final metrics.
7. Export a deterministic evidence ZIP with a package manifest, hashes, audit JSON, and human-readable Markdown report.
8. Preserve the current canonical Grokking Lab evidence logic as the first adapter.

## Later

- Generic arbitrary-repository execution.
- Docker/Nix environment reconstruction.
- TensorFlow/JAX adapters.
- W&B/MLflow integrations.
- Cloud GPU orchestration.
- Hyperparameter optimization.
- Model registry, dataset registry, RBAC, billing, production monitoring.
- LLM-assisted repository mapping (Gemini/Claude/OpenAI), strictly outside the verdict path.
- Browser UI beyond a thin upload/URL front end.

## User scenario

### Current supported path

```bash
grokking-lab audit --artifact-dir artifacts/p113_seed42_40k

grokking-lab compare \
  path/to/run_a \
  path/to/run_b

grokking-lab export \
  --artifact-dir artifacts/p113_seed42_40k \
  --output evidence.zip
```

Expected audit result shape:

```json
{
  "status": "PASS",
  "verdict": "VERIFIED",
  "adapter": "canonical_grokking_v1",
  "checks": [
    {"id": "base_evidence", "status": "PASS"},
    {"id": "environment", "status": "PASS"},
    {"id": "checksums", "status": "PASS"},
    {"id": "canonical_grokking_contract", "status": "PASS"},
    {"id": "replay", "status": "PASS"}
  ]
}
```

### Target product UX after the engine is stable

Input: GitHub URL, ZIP, or run directory.

Single primary action: **Verify experiment**.

Output: verdict, claimed vs replayed metrics, failed/incomplete checks, comparison option, and evidence-package download.

## Architecture

```text
CLI / thin web shell
        |
        v
Audit orchestration
        |
        +-- evidence presence + hashes
        +-- environment/config capture
        +-- experiment adapter
        +-- checkpoint replay
        +-- verdict policy
        +-- comparison
        +-- deterministic evidence export
```

The existing modular-addition Grokking experiment is `canonical_grokking_v1`, the first adapter and regression oracle.

## Verdict semantics

- `VERIFIED`: every required check passes.
- `FAILED`: at least one available piece of evidence contradicts the recorded claim or fails integrity/replay.
- `INCOMPLETE`: no contradiction is established, but required evidence is missing or cannot be evaluated.

`INCOMPLETE` must never be silently promoted to `VERIFIED`.

## Acceptance gate

v0.1 is ready when all of the following hold:

1. Existing canonical seed-42 evidence still passes unchanged.
2. Existing checkpoint replay still passes.
3. Corrupted hashed evidence produces `FAILED`.
4. Missing required evidence produces `INCOMPLETE`.
5. Comparison works for 2–5 runs.
6. Evidence export includes source files plus generated audit JSON, report, and manifest with SHA-256.
7. CI is green on a clean runner.
8. A second PyTorch adapter can use the same audit result schema without changing verdict semantics.
9. At least three external repositories/runs are attempted; failures to ingest are recorded as product evidence, not hidden.

## Two-week execution plan

### Week 1 — engine

- Day 1: freeze v0.1 contract and verdict semantics.
- Day 2: generic audit orchestration over current canonical evidence.
- Day 3: environment/config evidence normalization.
- Day 4: replay result normalization and tolerance policy.
- Day 5: 2–5 run comparison.
- Day 6: deterministic evidence-package export.
- Day 7: corruption/missing-evidence negative tests and CI hardening.

### Week 2 — applicability

- Day 8: adapter protocol and second simple PyTorch experiment.
- Day 9: import path for an external run directory.
- Day 10: GitHub-repository intake prototype with explicit unsupported states.
- Day 11: thin local web page: URL/ZIP -> Verify.
- Day 12: test against three external ML repositories.
- Day 13: improve diagnostics from real failures; no scope expansion.
- Day 14: freeze v0.1.0 candidate and produce one public evidence example.

## External validation targets

First users should be people who already pay the manual cost of reproducibility: artifact reviewers, reproducibility challenge participants, research engineers validating colleagues' runs, and small ML teams reviewing claimed improvements.

The first external test is not "do you like the idea?" It is: **give us a run/repository and see how much of the claimed result Grokking Lab can verify automatically.**
