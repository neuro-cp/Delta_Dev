import inspect
import learning.integrity_consensus.consensus_engine as mod

def test_consensus_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
