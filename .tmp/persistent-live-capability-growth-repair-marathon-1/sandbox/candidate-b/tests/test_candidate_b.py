import importlib.util
from pathlib import Path

def _load_candidate():
    path = Path(__file__).resolve().parents[1] / 'source' / 'candidate.py'
    spec = importlib.util.spec_from_file_location('candidate_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_candidate_predicts_without_runtime_imports():
    candidate = _load_candidate()
    result = candidate.predict({'turns': ['What is angular momentum?'], 'answer_obligation': 'foreground'})
    assert isinstance(result, str)
    assert result
