# arXiv paper package

Working title: **Reproducible Grokking in Modular Addition Across Three Independent Seeds**

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
paper/figures/three_seed_validation.png
```

The three-seed comparison figure is generated directly from the stored training time series for seeds 42, 43, and 44.

## Scope

The paper makes a deliberately narrow claim: three independent PyTorch runs with `p=113` and seeds 42, 43, and 44 exhibit delayed generalization under one fixed principal configuration. The package emphasizes replayable checkpoints, integrity metadata, and explicit reproducibility boundaries.

It does **not** claim universality across arbitrary seeds or a new mechanistic theory of grokking.

## Submission category

Provisional primary category: `cs.LG`.

Before submission:
- compile and inspect the PDF;
- confirm author metadata;
- include the figure in the upload bundle;
- verify references and arXiv category/endorsement requirements;
- optionally add ORCID once available.
