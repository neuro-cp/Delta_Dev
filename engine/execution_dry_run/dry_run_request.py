# dry_run_request.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from engine.execution_gate.execution_intent import ExecutionIntent

@dataclass(frozen=True)
class DryRunRequest:
    """
    Pure data wrapper for a dry-run request.
    """
    intent: ExecutionIntent
    binding_targets: Tuple[str, ...]
