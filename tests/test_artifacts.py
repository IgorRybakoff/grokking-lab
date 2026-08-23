from pathlib import Path

from grokking_lab.artifacts import verify_artifact_directory


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_evidence_integrity():
    result = verify_artifact_directory(ROOT / "artifacts" / "p113_seed42_40k")
    assert result["status"] == "PASS"
    assert result["events"]["grokking_candidate_step"] == 25600
    assert result["events"]["plateau_step"] == 26500

