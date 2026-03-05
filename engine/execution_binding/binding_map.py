from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from .binding_target import BindingTarget

@dataclass(frozen=True)
class BindingMap:
    """
    Describes conceptual bindings only.
    """
    intent_id: str
    targets: Tuple[BindingTarget, ...]
