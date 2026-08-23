from grokking_lab.config import ExperimentConfig


def test_canonical_config_is_valid():
    ExperimentConfig().validate()


def test_invalid_head_geometry_is_rejected():
    config = ExperimentConfig(d_model=127)
    try:
        config.validate()
    except ValueError as exc:
        assert "divisible" in str(exc)
    else:
        raise AssertionError("invalid config was accepted")

