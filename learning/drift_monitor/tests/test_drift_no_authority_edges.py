import inspect
import learning.drift_monitor.drift_engine as mod

def test_drift_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
