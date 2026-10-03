from pathlib import Path

from grokking_lab.audit import audit_run
from grokking_lab.compare import compare_runs


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "artifacts" / "p113_seed42_40k"


def test_existing_frozen_run_passes_mvp_audit_without_duplicate_replay():
    result = audit_run(FROZEN, replay=False)
    assert result["status"] == "PASS"
    assert result["verdict"] == "VERIFIED"
    assert result["adapter"] == "canonical_grokking_v1"
    assert all(check["status"] == "PASS" for check in result["checks"])


def test_missing_evidence_is_incomplete_not_verified(tmp_path):
    result = audit_run(tmp_path, replay=False)
    assert result["status"] == "INCOMPLETE"
    assert result["verdict"] == "INCOMPLETE"


def test_compare_reports_no_config_delta_for_identical_runs():
    result = compare_runs([FROZEN, FROZEN])
    assert result["status"] == "PASS"
    assert result["run_count"] == 2
    assert result["varying_config"] == {}
