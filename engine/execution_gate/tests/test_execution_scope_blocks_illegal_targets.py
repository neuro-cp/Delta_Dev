# test_execution_scope_blocks_illegal_targets.py
import pytest
from engine.execution_gate.execution_scope import ExecutionScope

def test_execution_scope_blocks_forbidden():
    scope = ExecutionScope(
        allowed_targets=frozenset({"attention"}),
        forbidden_targets=frozenset({"decision"}),
    )
    with pytest.raises(ValueError):
        scope.validate(frozenset({"decision"}))
