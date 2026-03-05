import inspect
import learning.integrity_pressure.integrity_engine as mod

def test_integrity_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
