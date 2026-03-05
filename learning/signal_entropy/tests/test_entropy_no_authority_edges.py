import inspect
import learning.signal_entropy.entropy_engine as mod

def test_entropy_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
