import inspect
import learning.governance_gate.gate_engine as mod

def test_gate_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
