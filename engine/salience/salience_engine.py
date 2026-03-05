from __future__ import annotations

from typing import Iterable, Any, Dict, List

from engine.salience.salience_field import SalienceField
from engine.salience.salience_policy import SaliencePolicy
from engine.salience.observations import collect_salience_observations
from engine.salience.salience_trace import SalienceTrace
from engine.salience.sources.salience_source import SalienceSource


class SalienceEngine:
    """
    Salience coordination engine.

    PURPOSE:
    - Collect read-only observations from the runtime
    - Query salience sources for proposed updates
    - Enforce SaliencePolicy
    - Inject approved updates into SalienceField
    - Record accepted proposals into an in-RAM trace buffer

    DESIGN GUARANTEES:
    - Stateless across steps (except trace buffer)
    - Deterministic given inputs
    - No runtime mutation
    - No learning
    - No decision authority
    """

    def __init__(self, sources: Iterable[SalienceSource]):
        self.sources: List[SalienceSource] = list(sources)
        self.trace = SalienceTrace()

    # --------------------------------------------------
    # Step
    # --------------------------------------------------

    def step(self, runtime: Any, field: SalienceField) -> None:
        """
        Execute one salience update step.

        ORDER:
        1. Collect observations (read-only)
        2. Ask each source for proposed updates
        3. Apply policy gating
        4. Inject approved updates into field
        5. Record approved updates into trace buffer
        """

        # --------------------------------------------------
        # 1. Collect observations (single canonical path)
        # --------------------------------------------------
        observations: Dict[str, Any] = collect_salience_observations(runtime)

        # Interpretive time, not neural time
        step = int(observations.get("step", -1))
        time = float(observations.get("time", 0.0))

        # --------------------------------------------------
        # 2. Query sources
        # --------------------------------------------------
        for source in self.sources:
            source_name = (
                getattr(source, "name", None)
                or getattr(source, "source_id", None)
                or source.__class__.__name__
            )

            try:
                raw_updates = source.compute(observations)
            except Exception:
                # Salience sources fail closed
                continue

            if raw_updates is None:
                continue

            # --------------------------------------------------
            # Normalize update shapes (explicit handshake)
            # --------------------------------------------------
            if isinstance(raw_updates, dict):
                iterable = (
                    {
                        "channel_id": channel_id,
                        "delta": delta,
                        "source": source_name,
                    }
                    for channel_id, delta in raw_updates.items()
                )
            else:
                iterable = raw_updates

            # --------------------------------------------------
            # 3–5. Gate, inject, record
            # --------------------------------------------------
            for u in iterable:
                if isinstance(u, dict):
                    channel_id = u.get("channel_id") or u.get("channel")
                    delta = u.get("delta")
                    src = u.get("source", source_name)
                else:
                    channel_id = getattr(u, "channel_id", None)
                    delta = getattr(u, "delta", None)
                    src = getattr(u, "source", source_name)

                if channel_id is None or delta is None:
                    continue

                try:
                    channel_id = str(channel_id)
                    delta = float(delta)
                    src = str(src)
                except Exception:
                    continue

                if not SaliencePolicy.allow_update(channel_id, delta):
                    continue

                field.inject(channel_id, delta)

                self.trace.record(
                    step=step,
                    time=time,
                    source=src,
                    channel_id=channel_id,
                    delta=delta,
                )
