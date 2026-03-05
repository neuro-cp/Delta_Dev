from dataclasses import dataclass
from typing import Set
from engine.execution.execution_target import ExecutionTarget

@dataclass(frozen=True)
class ExecutionMonitorRecord:
    active: bool
    targets: Set[ExecutionTarget]
