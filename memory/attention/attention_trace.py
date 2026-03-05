from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class AttentionTraceRecord:
    step: int
    event: str
    payload: Dict[str, Any]


class AttentionTrace:
    """
    Append-only attention trace.

    CONTRACT:
    - Observational only
    - No influence
    """

    def __init__(self) -> None:
        self._records: List[AttentionTraceRecord] = []

    def record(self, *, step: int, event: str, payload: Dict[str, Any]) -> None:
        self._records.append(
            AttentionTraceRecord(
                step=step,
                event=event,
                payload=dict(payload),
            )
        )

    def records(self) -> List[AttentionTraceRecord]:
        return list(self._records)
