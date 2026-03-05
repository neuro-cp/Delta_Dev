from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SalienceTraceEvent:
    step: int
    time: float
    source: str
    channel_id: str
    delta: float


class SalienceTrace:
    """
    Append-only, RAM-only salience proposal trace.
    No authority. No mutation of runtime.
    """

    def __init__(self, max_events: int = 10_000) -> None:
        self._events: List[SalienceTraceEvent] = []
        self._max = int(max_events)

    def record(
        self,
        *,
        step: int,
        time: float,
        source: str,
        channel_id: str,
        delta: float,
    ) -> None:
        self._events.append(
            SalienceTraceEvent(
                step=step,
                time=time,
                source=source,
                channel_id=channel_id,
                delta=delta,
            )
        )
        if len(self._events) > self._max:
            self._events.pop(0)

    def recent_events(self, n: int = 10) -> List[SalienceTraceEvent]:
        return self._events[-n:]
