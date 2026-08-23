#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from grokking_lab.replay import replay_checkpoint


parser = argparse.ArgumentParser()
parser.add_argument("--checkpoint", default="final_model_state.pt")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
result = replay_checkpoint(root / "artifacts" / "p113_seed42_40k", args.checkpoint)
print(json.dumps(result, indent=2))
raise SystemExit(0 if result["status"] == "PASS" else 1)

