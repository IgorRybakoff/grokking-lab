# arXiv paper package

Working title: **A Reproducible Baseline for Grokking in Modular Addition**

## Build

From the `paper/` directory:

```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

The manuscript expects the figure at:

```
paper/figures/grokking_curve.png
```

The source figure is generated from the frozen run at:

```
artifacts/p113_seed42_40k/plots/grokking_curve.png
```

## Scope

The paper makes a deliberately narrow claim: one frozen PyTorch run with `p=113`, seed 42, and the documented event policy exhibits delayed generalization and is packaged with replayable checkpoints, integrity metadata, and explicit reproducibility boundaries.

It does **not** claim universality across seeds or a new mechanistic theory of grokking.

## Submission category

Provisional primary category: `cs.LG`.

Before submission:
- compile and inspect the PDF;
- confirm author metadata;
- include the figure in the upload bundle;
- verify references and arXiv category/endorsement requirements;
- optionally add ORCID once available.
