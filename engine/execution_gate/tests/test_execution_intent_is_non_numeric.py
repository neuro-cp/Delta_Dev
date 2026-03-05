# test_execution_intent_is_non_numeric.py
from engine.execution_gate.execution_intent import ExecutionIntent
import pytest

def test_execution_intent_rejects_non_string_targets():
    with pytest.raises(TypeError):
        ExecutionIntent("i2", ("attention", 3))  # type: ignore
