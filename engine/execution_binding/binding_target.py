from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class BindingTarget:
    """
    Declarative target reference.
    """
    target_id: str
