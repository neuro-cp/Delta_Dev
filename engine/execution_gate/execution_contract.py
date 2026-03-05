# execution_contract.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ExecutionContract:
    """
    Canonical definition of what execution means and does NOT mean.

    This contract is descriptive only.
    It confers no authority, performs no action, and wires to nothing.
    """

    execution_defined: bool = True
    execution_enabled: bool = False

    prohibits_runtime_coupling: bool = True
    prohibits_replay_coupling: bool = True
    prohibits_learning_coupling: bool = True

    non_numeric_only: bool = True
    record_only: bool = True
