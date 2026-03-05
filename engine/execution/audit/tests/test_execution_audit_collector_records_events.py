from engine.execution.audit.execution_audit_event import ExecutionAuditEvent
from engine.execution.audit.execution_audit_collector import ExecutionAuditCollector
from engine.execution.execution_target import ExecutionTarget

def test_collector_records():
    c = ExecutionAuditCollector()
    e = ExecutionAuditEvent(True, {ExecutionTarget.VALUE_BIAS}, "ok")
    c.record(e)
    assert c.events == (e,)
