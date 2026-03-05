# engine/cognition/audit/hypothesis_audit_trace.py
from __future__ import annotations

from typing import Iterable, List

from .hypothesis_audit_event import HypothesisAuditEvent


class HypothesisAuditTrace:
    """
    Append-only audit trace for offline cognition analysis.

    This class is deliberately inert:
    - no thresholds
    - no interpretation
    - no mutation of hypotheses
    """

    def __init__(self) -> None:
        self._events: List[HypothesisAuditEvent] = []

    def append(self, event: HypothesisAuditEvent) -> None:
        self._events.append(event)

    def extend(self, events: Iterable[HypothesisAuditEvent]) -> None:
        for e in events:
            self.append(e)

    @property
    def events(self) -> List[HypothesisAuditEvent]:
        # defensive copy: forensic integrity
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)
