from learning.drive_bias.selection.bias_selector import BiasSelector


def test_selection_respects_threshold():
    selector = BiasSelector()

    scores = {"a": 0.5, "b": 1.5, "c": 2.0}

    selected = selector.compute_selection(scores, threshold=1.0)

    assert selected == ["c", "b"]
