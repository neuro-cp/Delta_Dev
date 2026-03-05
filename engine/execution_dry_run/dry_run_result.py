# dry_run_result.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class DryRunResult:
    intent_id: str
    simulated_targets: Tuple[str, ...]
    allowed: bool
    reason: str
