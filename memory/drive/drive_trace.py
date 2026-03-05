from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass(frozen=True)
class DriveTraceRecord:
    step: int
    event: str
    payload: Dict[str, Any]


class DriveTrace:
    """
    Append-only drive trace.

    CONTRACT:
    - Observational only
    """

    def __init__(self) -> None:
        self._records: List[DriveTraceRecord] = []

    def record(self, *, step: int, event: str, payload: Dict[str, Any]) -> None:
        self._records.append(
            DriveTraceRecord(
                step=step,
                event=event,
                payload=dict(payload),
            )
        )

    def records(self) -> List[DriveTraceRecord]:
        return list(self._records)
