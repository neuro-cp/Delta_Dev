import inspect
import learning.drive_bias.selection.bias_selector as module


def test_selection_no_authority_edges():
    source = inspect.getsource(module)
    assert "engine." not in source
