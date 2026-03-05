from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class WorkingMemoryTraceRecord:
    step: int
    event: str
    payload: Dict[str, Any]


class WorkingMemoryTrace:
    """
    Append-only trace of working memory activity.

    CONTRACT:
    - Observational only
    - No influence
    """

    def __init__(self) -> None:
        self._records: List[WorkingMemoryTraceRecord] = []

    def record(self, *, step: int, event: str, payload: Dict[str, Any]) -> None:
        self._records.append(
            WorkingMemoryTraceRecord(
                step=step,
                event=event,
                payload=dict(payload),
            )
        )

    def records(self) -> List[WorkingMemoryTraceRecord]:
        return list(self._records)
