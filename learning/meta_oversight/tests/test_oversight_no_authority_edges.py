import inspect
import learning.meta_oversight.oversight_engine as mod

def test_oversight_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
