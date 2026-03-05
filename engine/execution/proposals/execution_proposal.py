from dataclasses import dataclass
from typing import Set
from engine.execution.execution_target import ExecutionTarget

@dataclass(frozen=True)
class ExecutionProposal:
    source: str
    suggested_targets: Set[ExecutionTarget]
    confidence: float
