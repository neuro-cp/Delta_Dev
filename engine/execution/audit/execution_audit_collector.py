from .execution_audit_event import ExecutionAuditEvent

class ExecutionAuditCollector:
    def __init__(self):
        self._events: list[ExecutionAuditEvent] = []

    def record(self, event: ExecutionAuditEvent) -> None:
        self._events.append(event)

    @property
    def events(self):
        return tuple(self._events)
