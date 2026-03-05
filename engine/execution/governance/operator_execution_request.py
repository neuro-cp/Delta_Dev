from dataclasses import dataclass
from typing import Optional, Set

from engine.execution.execution_target import ExecutionTarget


@dataclass(frozen=True)
class OperatorExecutionRequest:
    """
    Declarative request by an operator to enable execution.

    This object carries intent only and has no authority.
    """
    operator_id: str
    requested_targets: Optional[Set[ExecutionTarget]]
    justification: str
