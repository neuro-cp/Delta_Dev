from __future__ import annotations

from typing import List

from .observation_engine import ObservationEngine
from .observation_event import ObservationEvent


class ObservationRuntimeHook:
    """
    Read-only runtime hook.

    Attaches to BrainRuntime and *observes* settled state.
    Never mutates runtime, never feeds back into execution.
    """

    def __init__(self):
        self.engine = ObservationEngine()
        self.events: List[ObservationEvent] = []

    def step(self, runtime) -> None:
        """
        Observe runtime after dynamics have settled.

        Called once per BrainRuntime.step().
        """
        step = runtime.step_count

        # Iterate regions deterministically
        for region_key in sorted(runtime.region_states.keys()):
            stats = runtime.snapshot_region_stats(region_key)
            if not stats:
                continue

            mass = float(stats.get("mass", 0.0))
            fraction_active = self._fraction_active(runtime, region_key)

            new_events = self.engine.step(
                step=step,
                region=region_key,
                mass=mass,
                fraction_active=fraction_active,
            )

            if new_events:
                self.events.extend(new_events)

    # ------------------------------------------------------------
    # Helpers (read-only)
    # ------------------------------------------------------------

    @staticmethod
    def _fraction_active(runtime, region_key: str) -> float:
        """
        Fraction of assemblies with output > 0.
        """
        region = runtime.region_states.get(region_key)
        if not region:
            return 0.0

        total = 0
        active = 0

        for plist in region.get("populations", {}).values():
            for pop in plist:
                total += 1
                if pop.output() > 0.0:
                    active += 1

        return (active / total) if total else 0.0