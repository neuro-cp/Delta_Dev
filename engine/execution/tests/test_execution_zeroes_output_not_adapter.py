from engine.execution.execution_gate import ExecutionGate
from engine.execution.execution_state import ExecutionState
from engine.execution.execution_target import ExecutionTarget


def test_execution_zeroes_output_not_adapter():
    gate = ExecutionGate(
        ExecutionState(enabled=True, allowed_targets={ExecutionTarget.VALUE_BIAS})
    )
    out = gate.apply(ExecutionTarget.URGENCY_RELIEF, value=0.2, identity=0.0)
    assert out == 0.0
    assert gate.records[0].applied is False
