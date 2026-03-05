import inspect
import learning.calibration_application.application_engine as mod

def test_application_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
