from __future__ import annotations
from typing import List
from .observation_event import ObservationEvent
from .observation_schema import ObservationType
from .observation_policy import ObservationPolicy


class ObservationEngine:
    """
    Stateless observer that evaluates runtime snapshots
    and emits ObservationEvents.
    """

    def __init__(self):
        self._last_mass = {}
        self._last_fraction = {}

    def step(self, *, step: int, region: str, mass: float, fraction_active: float) -> List[ObservationEvent]:
        events: List[ObservationEvent] = []

        last_mass = self._last_mass.get(region, mass)
        last_frac = self._last_fraction.get(region, fraction_active)

        dm = mass - last_mass
        df = fraction_active - last_frac

        if ObservationPolicy.should_emit_mass_shift(dm):
            events.append(
                ObservationEvent(
                    step=step,
                    region=region,
                    event_type=ObservationType.MASS_SHIFT.value,
                    payload={"delta": dm, "mass": mass},
                )
            )

        if ObservationPolicy.should_emit_fraction_change(df):
            events.append(
                ObservationEvent(
                    step=step,
                    region=region,
                    event_type=ObservationType.FRACTION_ACTIVE.value,
                    payload={"delta": df, "fraction_active": fraction_active},
                )
            )

        self._last_mass[region] = mass
        self._last_fraction[region] = fraction_active

        return events
