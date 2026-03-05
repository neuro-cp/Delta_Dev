from learning.drive_bias.selection.bias_selector import BiasSelector


def test_selection_is_read_only():
    selector = BiasSelector()

    scores = {"a": 1.0, "b": 2.0}
    original = dict(scores)

    selector.compute_selection(scores)

    assert scores == original
