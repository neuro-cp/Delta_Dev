from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class BindingResult:
    intent_id: str
    bound_targets: Tuple[str, ...]
    resolved: bool
    reason: str
