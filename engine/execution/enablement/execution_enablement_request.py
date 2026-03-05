from dataclasses import dataclass
from typing import Set

from engine.execution.execution_target import ExecutionTarget


@dataclass(frozen=True)
class ExecutionEnablementRequest:
    """
    Declarative request to enable execution for a limited scope.
    """
    targets: Set[ExecutionTarget]
    duration_steps: int
