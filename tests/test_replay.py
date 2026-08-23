from pathlib import Path

import pytest

from grokking_lab.replay import replay_checkpoint


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("checkpoint", ["memorization_model_state.pt", "final_model_state.pt"])
def test_checkpoint_replay(checkpoint):
    result = replay_checkpoint(ROOT / "artifacts" / "p113_seed42_40k", checkpoint)
    assert result["status"] == "PASS"

