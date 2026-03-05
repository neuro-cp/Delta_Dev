from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class BindingContract:
    """
    Describes how execution *would* be bound to subsystems.

    This contract performs no binding.
    """
    binding_defined: bool = True
    binding_active: bool = False
    prohibits_runtime_wiring: bool = True
    prohibits_learning_wiring: bool = True
    prohibits_replay_wiring: bool = True
