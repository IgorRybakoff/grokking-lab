#!/usr/bin/env python3
import argparse
import json

from grokking_lab.config import ExperimentConfig
from grokking_lab.train import run_training


parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
result = run_training(ExperimentConfig.from_json(args.config), args.output)
print(json.dumps(result, indent=2))

