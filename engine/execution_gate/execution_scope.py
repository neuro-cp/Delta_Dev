# execution_scope.py
from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet

@dataclass(frozen=True)
class ExecutionScope:
    """
    Defines which conceptual subsystems may ever be referenced.
    """
    allowed_targets: FrozenSet[str]
    forbidden_targets: FrozenSet[str]

    def validate(self, intent_targets: FrozenSet[str]) -> None:
        illegal = intent_targets & self.forbidden_targets
        if illegal:
            raise ValueError(f"Forbidden execution targets: {illegal}")
