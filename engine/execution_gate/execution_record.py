# execution_record.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class ExecutionRecord:
    """
    Immutable inspection artifact.
    """
    intent_id: str
    targets: Tuple[str, ...]
    authorized: bool
    executed: bool
    reason: str
