from __future__ import annotations

import argparse
import json

from .artifacts import verify_artifact_directory
from .audit import audit_run
from .compare import compare_runs
from .config import ExperimentConfig
from .evidence import export_evidence_package
from .replay import replay_checkpoint
from .train import run_training


def main() -> None:
    parser = argparse.ArgumentParser(prog="grokking-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("smoke", "train"):
        child = subparsers.add_parser(command)
        child.add_argument("--config", required=True)
        child.add_argument("--output", required=True)

    verify = subparsers.add_parser("verify", help="Verify the frozen canonical Grokking Lab evidence contract")
    verify.add_argument("--artifact-dir", required=True)

    replay = subparsers.add_parser("replay", help="Replay one checkpoint and compare recorded metrics")
    replay.add_argument("--artifact-dir", required=True)
    replay.add_argument("--checkpoint", default="final_model_state.pt")

    audit = subparsers.add_parser("audit", help="Run the MVP experiment audit and return VERIFIED/FAILED/INCOMPLETE")
    audit.add_argument("--artifact-dir", required=True)
    audit.add_argument("--checkpoint", default="final_model_state.pt")
    audit.add_argument("--no-replay", action="store_true")

    compare = subparsers.add_parser("compare", help="Compare 2-5 frozen runs")
    compare.add_argument("artifact_dirs", nargs="+")

    export = subparsers.add_parser("export", help="Create a deterministic evidence ZIP")
    export.add_argument("--artifact-dir", required=True)
    export.add_argument("--checkpoint", default="final_model_state.pt")
    export.add_argument("--output")

    args = parser.parse_args()
    if args.command in ("smoke", "train"):
        result = run_training(ExperimentConfig.from_json(args.config), args.output)
    elif args.command == "verify":
        result = verify_artifact_directory(args.artifact_dir)
    elif args.command == "replay":
        result = replay_checkpoint(args.artifact_dir, args.checkpoint)
    elif args.command == "audit":
        result = audit_run(args.artifact_dir, checkpoint=args.checkpoint, replay=not args.no_replay)
    elif args.command == "compare":
        result = compare_runs(args.artifact_dirs)
    else:
        result = export_evidence_package(args.artifact_dir, args.output, checkpoint=args.checkpoint)

    print(json.dumps(result, indent=2, default=str))
    if result.get("status") == "FAIL":
        raise SystemExit(1)
    if result.get("status") == "INCOMPLETE":
        raise SystemExit(2)
