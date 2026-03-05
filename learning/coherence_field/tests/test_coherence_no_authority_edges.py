import inspect
import learning.coherence_field.coherence_engine as mod

def test_coherence_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
