# execution_intent.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class ExecutionIntent:
    """
    Declarative description of a requested influence.

    Contains no numeric magnitude and no wiring.
    """
    intent_id: str
    targets: Tuple[str, ...]

    def __post_init__(self):
        for t in self.targets:
            if not isinstance(t, str):
                raise TypeError("ExecutionIntent targets must be strings")
