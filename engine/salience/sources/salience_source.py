# engine/salience/sources/salience_source.py
from __future__ import annotations

from typing import Dict, Iterable, Optional

from engine.salience.sources.sources import SalienceSource, SalienceUpdate


class BaseSalienceSource:
    """
    Canonical base class for salience sources.

    PURPOSE:
    - Provide a common structure for all salience sources
    - Enforce naming and safe emission patterns
    - Keep sources simple, explicit, and testable

    DESIGN:
    - Stateless by default
    - No runtime access
    - No direct salience mutation
    """

    #: Human-readable, stable identifier (override in subclasses)
    name: str = "base"

    #: Hard per-source delta cap (extra safety layer)
    max_delta: float = 0.05

    def __init__(self) -> None:
        if not self.name or self.name == "base":
            raise ValueError(
                f"{self.__class__.__name__} must define a non-default `name`"
            )

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def compute(
        self, observation: Dict[str, float]
    ) -> Iterable[SalienceUpdate]:
        """
        Entry point called by salience engine / runtime.

        Subclasses should NOT override this.
        They should override `_compute_delta`.
        """
        updates = []

        for channel_id, delta in self._compute_delta(observation).items():
            if not channel_id:
                continue

            clipped = self._clip(delta)
            if clipped == 0.0:
                continue

            updates.append(
                SalienceUpdate(
                    channel_id=channel_id,
                    delta=clipped,
                    source=self.name,
                )
            )

        return updates

    # ------------------------------------------------------------
    # To be implemented by subclasses
    # ------------------------------------------------------------

    def _compute_delta(
        self, observation: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compute proposed salience deltas per channel.

        Must return:
            Dict[channel_id -> delta]

        Rules:
        - May return empty dict
        - Must NOT clamp
        - Must NOT apply policy
        - Must NOT mutate state
        """
        raise NotImplementedError

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _clip(self, delta: float) -> float:
        """
        Apply per-source safety clipping.

        This is NOT the global SaliencePolicy clamp.
        """
        if delta > self.max_delta:
            return self.max_delta
        if delta < -self.max_delta:
            return -self.max_delta
        return delta
