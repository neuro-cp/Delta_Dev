from __future__ import annotations

from typing import Dict, Iterable, List

from engine.salience.sources.sources import SalienceSource, SalienceUpdate
from persistence.persistence_core import ExponentialTrace


class SensoryPersistenceSource(SalienceSource):
    """
    Observational salience source driven by sustained sensory mass deviation.

    Purpose:
    - Detect persistent, non-baseline sensory activity
    - Convert slow sensory pressure into weak, bounded salience proposals
    - Never trigger decisions
    - Never bypass salience policy or sparsity gate

    This source is intentionally conservative.
    """

    name = "sensory_persistence"

    def __init__(
        self,
        *,
        sensory_regions: Iterable[str],
        decay_tau: float = 2.5,
        gain: float = 0.05,
        min_delta: float = 1e-6,
    ) -> None:
        self.sensory_regions = tuple(sensory_regions)
        self.gain = float(gain)
        self.min_delta = float(min_delta)

        # One persistence trace per sensory region
        self._traces: Dict[str, ExponentialTrace] = {
            r: ExponentialTrace(decay_tau=decay_tau)
            for r in self.sensory_regions
        }

    # ------------------------------------------------------------------
    # SalienceSource interface
    # ------------------------------------------------------------------

    def compute(self, observation: Dict[str, float]) -> Iterable[SalienceUpdate]:
        """
        Emit salience proposals based on persistent sensory mass deviation.

        Expected observation keys:
            - "region_mass:<region_id>"
            - "region_mass_baseline:<region_id>"
            - "dt"
        """

        dt = float(observation.get("dt", 0.0))
        updates: List[SalienceUpdate] = []

        for region_id in self.sensory_regions:
            mass = observation.get(f"region_mass:{region_id}")
            baseline = observation.get(f"region_mass_baseline:{region_id}")

            if mass is None or baseline is None:
                continue

            deviation = mass - baseline

            # Ignore numerical noise and sign flips
            if deviation <= self.min_delta:
                self._traces[region_id].step(0.0, dt)
                continue

            # Integrate persistence
            trace_value = self._traces[region_id].step(deviation, dt)

            # Propose a very small, bounded salience increment
            delta = trace_value * self.gain

            if delta > self.min_delta:
                updates.append(
                    SalienceUpdate(
                        channel_id=region_id,
                        delta=delta,
                        source=self.name,
                    )
                )

        return updates

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Hard reset all persistence traces."""
        for trace in self._traces.values():
            trace.reset()
