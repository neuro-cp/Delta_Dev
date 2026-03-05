import inspect
import learning.adaptive_calibration.calibration_engine as mod

def test_calibration_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
