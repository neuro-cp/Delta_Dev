import inspect
import learning


def test_learning_has_no_engine_runtime_imports():
    source = inspect.getsource(learning)
    forbidden = ["engine.runtime", "decision", "salience", "routing"]

    for f in forbidden:
        assert f not in source
