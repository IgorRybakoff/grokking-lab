from __future__ import annotations

import argparse
import json

from .artifacts import verify_artifact_directory
from .config import ExperimentConfig
from .replay import replay_checkpoint
from .train import run_training


def main() -> None:
    parser = argparse.ArgumentParser(prog="grokking-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("smoke", "train"):
        child = subparsers.add_parser(command)
        child.add_argument("--config", required=True)
        child.add_argument("--output", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--artifact-dir", required=True)

    replay = subparsers.add_parser("replay")
    replay.add_argument("--artifact-dir", required=True)
    replay.add_argument("--checkpoint", default="final_model_state.pt")

    args = parser.parse_args()
    if args.command in ("smoke", "train"):
        result = run_training(ExperimentConfig.from_json(args.config), args.output)
    elif args.command == "verify":
        result = verify_artifact_directory(args.artifact_dir)
    else:
        result = replay_checkpoint(args.artifact_dir, args.checkpoint)
    print(json.dumps(result, indent=2))
    if result.get("status") == "FAIL":
        raise SystemExit(1)

