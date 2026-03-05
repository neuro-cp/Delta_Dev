import inspect
import learning.containment_envelope.envelope_engine as mod

def test_envelope_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
