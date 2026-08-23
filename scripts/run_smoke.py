#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from grokking_lab.config import ExperimentConfig
from grokking_lab.train import run_training


parser = argparse.ArgumentParser()
parser.add_argument("--output", default="runs/smoke")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
result = run_training(ExperimentConfig.from_json(root / "configs" / "smoke_p113_seed42.json"), args.output)
print(json.dumps(result, indent=2))

