from __future__ import annotations


class VisualTemporalDriver:
    """
    CHEATING sensory driver (temporal, delta-correct).

    Purpose:
    - Force VISUAL_INPUT above baseline
    - Sustain drive long enough to propagate through LGN → V1 → Pulvinar
    - Create a sharp ON / OFF temporal boundary
    - Explicitly remove stimulus on OFF (no accumulation)

    Notes:
    - Uses delta-based injection because runtime stimulus injection is additive
    - Does NOT modify runtime or population dynamics
    - This is a test driver, not a biological model
    """

    def __init__(
        self,
        *,
        onset_step: int = 20,
        offset_step: int = 160,
        magnitude: float = 0.25,
    ) -> None:
        self.onset_step = onset_step
        self.offset_step = offset_step
        self.magnitude = magnitude

        self.step_count = 0
        self._last_signal: float = 0.0  # tracks what is currently applied

    def step(self, runtime) -> None:
        self.step_count += 1

        # Desired signal level for this step
        if self.onset_step <= self.step_count <= self.offset_step:
            target_signal = self.magnitude
        else:
            target_signal = 0.0

        # Compute delta because injection is additive
        delta = target_signal - self._last_signal

        if delta != 0.0:
            runtime.inject_stimulus(
                region_id="visual_input",
                population_id="VISUAL_SIGNAL",
                magnitude=delta,
            )

        # Update state
        self._last_signal = target_signal
