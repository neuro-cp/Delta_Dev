# dry_run_trace.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .dry_run_result import DryRunResult

@dataclass(frozen=True)
class DryRunTrace:
    """
    Immutable dry-run trace for inspection.
    """
    results: List[DryRunResult]
