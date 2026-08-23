#!/usr/bin/env python3
import json
from pathlib import Path

from grokking_lab.artifacts import verify_artifact_directory


ROOT = Path(__file__).resolve().parents[1]
result = verify_artifact_directory(ROOT / "artifacts" / "p113_seed42_40k")
print(json.dumps(result, indent=2))

