from dataclasses import dataclass
from typing import Set
from engine.execution.execution_target import ExecutionTarget

@dataclass(frozen=True)
class GovernanceEnablementRequest:
    targets: Set[ExecutionTarget]
    duration_steps: int
    rationale: str
