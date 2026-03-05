import inspect
import learning.cognitive_evaluation.cognitive_evaluation_engine as mod

def test_evaluation_no_authority_edges():
    src = inspect.getsource(mod)
    assert "engine.runtime" not in src
