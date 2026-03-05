from dataclasses import dataclass
from typing import Any

from .execution_target import ExecutionTarget


@dataclass(frozen=True)
class ExecutionRecord:
    target: ExecutionTarget
    applied: bool
    value_snapshot: Any
