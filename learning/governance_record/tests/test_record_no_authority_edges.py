import inspect
import learning.governance_record.record_engine as mod

def test_record_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
