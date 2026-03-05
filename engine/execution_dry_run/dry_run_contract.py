# dry_run_contract.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DryRunContract:
    """
    Defines dry-run execution semantics.

    Dry-runs simulate execution paths but never
    perform execution or influence.
    """
    dry_run_enabled: bool = True
    execution_allowed: bool = False
    prohibits_runtime_access: bool = True
    prohibits_learning_access: bool = True
    prohibits_replay_access: bool = True
