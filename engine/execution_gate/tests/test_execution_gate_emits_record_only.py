# test_execution_gate_emits_record_only.py
from engine.execution_gate.execution_gate import ExecutionGate
from engine.execution_gate.execution_intent import ExecutionIntent
from engine.execution_gate.execution_authorization import ExecutionAuthorization
from engine.execution_gate.execution_scope import ExecutionScope
from engine.execution_gate.execution_record import ExecutionRecord

def test_execution_gate_emits_record_only():
    scope = ExecutionScope(
        allowed_targets=frozenset({"attention"}),
        forbidden_targets=frozenset(),
    )
    gate = ExecutionGate(scope)
    intent = ExecutionIntent("i3", ("attention",))
    auth = ExecutionAuthorization(True)

    record = gate.attempt(intent, auth)
    assert isinstance(record, ExecutionRecord)
    assert record.executed is False
