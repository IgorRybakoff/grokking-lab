import json

from grokking_lab.config import ExperimentConfig
from grokking_lab.train import run_training


def test_real_pytorch_smoke_changes_parameters(tmp_path):
    config = ExperimentConfig(max_steps=1, log_interval=1, run_mode="test_smoke")
    result = run_training(config, tmp_path)
    assert result["engine_type"] == "pytorch_core"
    assert result["parameters_changed"] is True
    manifest = json.loads((tmp_path / "experiment_manifest.json").read_text())
    assert manifest["simulated_metrics"] is False
    assert manifest["llm_generated_metrics"] is False

