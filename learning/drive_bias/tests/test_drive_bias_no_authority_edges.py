import inspect
import learning.drive_bias.drive_bias_engine as module


def test_drive_bias_no_authority_edges():
    source = inspect.getsource(module)
    assert "engine." not in source
