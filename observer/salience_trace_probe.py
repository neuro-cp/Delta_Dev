from __future__ import annotations

from typing import Any


class SalienceTraceProbe:
    """
    Passive observer that reports salience trace activity.

    - No authority
    - No mutation
    - Debug / verification only
    """

    name = "salience_trace_probe"

    def observe(self, snapshot: dict) -> None:
        """
        Called once per runtime step.
        """

        events = snapshot.get("salience_trace_events")
        if not events:
            return

        # Print only the most recent event to avoid spam
        evt = events[-1]

        print(
            f"[SAL_TRACE] step={snapshot.get('step')} "
            f"src={evt.source} "
            f"ch={evt.channel_id} "
            f"Δ={evt.delta:.6f}"
        )
