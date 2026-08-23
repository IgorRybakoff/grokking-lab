from grokking_lab.data import make_modular_addition_data


def test_dataset_and_split_match_frozen_protocol():
    data = make_modular_addition_data(113, 0.3, 42)
    assert len(data.train_indices) == 3830
    assert len(data.validation_indices) == 8939
    assert data.split_sha256 == "447b85aa50b551871fa7e136c40ded3a0925734e6200e909dea17455c57662bd"
    assert data.train_tokens.shape[1] == 3
    assert (data.train_tokens[:, 2] == 113).all()

