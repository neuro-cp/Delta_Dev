from engine.execution.audit.execution_audit_event import ExecutionAuditEvent
from engine.execution.execution_target import ExecutionTarget

def test_event_is_pure_data():
    e = ExecutionAuditEvent(True, {ExecutionTarget.VALUE_BIAS}, "test")
    for v in e.__dict__.values():
        assert not callable(v)
