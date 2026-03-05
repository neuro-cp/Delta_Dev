# engine/cognition/audit/hypothesis_audit_event.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class HypothesisAuditEvent:
    """
    Immutable audit event emitted during offline cognition inspection.

    This is observational only. Events describe *what happened*,
    never *what should happen*.
    """
    event: str
    step: int
    hypothesis_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
