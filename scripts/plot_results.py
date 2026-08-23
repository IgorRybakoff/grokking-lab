#!/usr/bin/env python3
import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
artifact = ROOT / "artifacts" / "p113_seed42_40k"
rows = json.loads((artifact / "training_timeseries.json").read_text(encoding="utf-8"))
steps = [row["step"] for row in rows]
train = [100.0 * row["train_acc"] for row in rows]
validation = [100.0 * row["val_acc"] for row in rows]

plt.figure(figsize=(10, 5.4), dpi=160)
plt.plot(steps, train, label="Train accuracy", linewidth=2.0)
plt.plot(steps, validation, label="Validation accuracy", linewidth=2.2)
for step, label in ((200, "memorization"), (25600, "candidate"), (26500, "plateau")):
    plt.axvline(step, color="#8a8a8a", linewidth=0.8, linestyle="--")
    plt.text(step + 350, 8 if step == 200 else 18, label, rotation=90, color="#555555", fontsize=8)
plt.title("Delayed generalization on modular addition (p=113, seed=42)")
plt.xlabel("Optimizer step")
plt.ylabel("Accuracy (%)")
plt.xlim(0, 40000)
plt.ylim(-2, 102)
plt.grid(alpha=0.2)
plt.legend(loc="center right")
plt.tight_layout()
plt.savefig(artifact / "plots" / "grokking_curve.png")

