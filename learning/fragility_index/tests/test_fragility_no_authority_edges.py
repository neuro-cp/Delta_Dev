import inspect
import learning.fragility_index.fragility_engine as mod

def test_fragility_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
