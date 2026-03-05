# dry_run_context.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DryRunContext:
    """
    Context snapshot for a dry-run.

    Contains no runtime state.
    """
    context_id: str
