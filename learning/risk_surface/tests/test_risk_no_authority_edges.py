import inspect
import learning.risk_surface.risk_engine as mod

def test_risk_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
