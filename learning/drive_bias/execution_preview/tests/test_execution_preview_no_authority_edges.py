import inspect
import learning.drive_bias.execution_preview.execution_preview_engine as mod

def test_execution_preview_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
