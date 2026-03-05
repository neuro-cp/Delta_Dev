import inspect
import learning.stability_model.stability_engine as mod

def test_stability_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
