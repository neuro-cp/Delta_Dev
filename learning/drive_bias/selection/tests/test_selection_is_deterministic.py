from learning.drive_bias.selection.bias_selector import BiasSelector


def test_selection_is_deterministic():
    selector = BiasSelector()

    scores = {"a": 1.0, "b": 2.0, "c": 2.0}

    first = selector.compute_selection(scores)
    second = selector.compute_selection(scores)

    assert first == second
