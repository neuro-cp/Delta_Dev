from dataclasses import dataclass
from typing import Set

from engine.execution.execution_target import ExecutionTarget


@dataclass(frozen=True)
class ExecutionEnablementRecord:
    enabled: bool
    targets: Set[ExecutionTarget]
    remaining_steps: int
