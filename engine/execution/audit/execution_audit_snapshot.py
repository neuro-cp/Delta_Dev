from dataclasses import dataclass
from typing import Tuple
from .execution_audit_event import ExecutionAuditEvent

@dataclass(frozen=True)
class ExecutionAuditSnapshot:
    events: Tuple[ExecutionAuditEvent, ...]
