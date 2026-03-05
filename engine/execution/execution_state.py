from dataclasses import dataclass
from typing import Optional, Set

from .execution_target import ExecutionTarget


@dataclass(frozen=True)
class ExecutionState:
    enabled: bool = False
    allowed_targets: Optional[Set[ExecutionTarget]] = None

    def is_allowed(self, target: ExecutionTarget) -> bool:
        if not self.enabled:
            return False
        if self.allowed_targets is None:
            return True
        return target in self.allowed_targets
