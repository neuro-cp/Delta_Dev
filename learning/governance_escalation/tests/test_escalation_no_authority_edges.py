import inspect
import learning.governance_escalation.escalation_engine as mod

def test_escalation_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
