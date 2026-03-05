# test_execution_gate_closed_by_default.py
from engine.execution_gate.execution_gate import ExecutionGate
from engine.execution_gate.execution_intent import ExecutionIntent
from engine.execution_gate.execution_authorization import ExecutionAuthorization
from engine.execution_gate.execution_scope import ExecutionScope

def test_execution_gate_closed_by_default():
    scope = ExecutionScope(
        allowed_targets=frozenset({"attention"}),
        forbidden_targets=frozenset({"decision", "learning"}),
    )
    gate = ExecutionGate(scope)

    intent = ExecutionIntent("i1", ("attention",))
    auth = ExecutionAuthorization(authorized=False)

    record = gate.attempt(intent, auth)
    assert record.executed is False
