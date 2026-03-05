from __future__ import annotations

from typing import Dict, Iterable


class SaliencePolicy:
    """
    Salience update policy.

    PURPOSE:
    - Propose salience updates from physiology
    - Gate which updates are allowed
    - Enforce bounded, biologically plausible influence
    - Prevent salience from becoming a covert decision system

    DESIGN PRINCIPLES:
    - Stateless
    - Deterministic
    - Conservative by default
    """

    # ------------------------------------------------------------
    # Hard limits (global safety rails)
    # ------------------------------------------------------------

    MAX_DELTA = 0.05          # single injection cap
    MAX_ABS_SALIENCE = 1.0   # should match SalienceField.max_salience
    EPSILON = 1e-6

    # ------------------------------------------------------------
    # Proposal thresholds (physiology → salience)
    # ------------------------------------------------------------

    ACTIVITY_THRESHOLD = 0.02
    FIRING_THRESHOLD = 0.05

    ACTIVITY_GAIN = 1.0
    FIRING_GAIN = 0.5

    INHIBITORY_SCALE = 0.6
    INTERNEURON_SCALE = 0.5
    SENSORY_SCALE = 1.2

    # ------------------------------------------------------------
    # Proposal stage
    # ------------------------------------------------------------

    @classmethod
    def propose_updates(cls, populations: Iterable) -> Dict[str, float]:
        """
        Generate conservative salience proposals from physiology.

        This does NOT mutate salience.
        It only proposes bounded deltas.
        """
        proposals: Dict[str, float] = {}

        for pop in populations:
            channel_id = pop.assembly_id
            if not channel_id:
                continue

            delta = 0.0

            # Activity deviation
            activity_dev = abs(pop.activity - pop.baseline)
            if activity_dev > cls.ACTIVITY_THRESHOLD:
                delta += cls.ACTIVITY_GAIN * activity_dev

            # Firing contribution
            if pop.firing_rate > cls.FIRING_THRESHOLD:
                delta += cls.FIRING_GAIN * pop.firing_rate

            if delta <= cls.EPSILON:
                continue

            # Semantic scaling
            role = (pop.semantic_role or "").lower()

            if pop.sign < 0:
                delta *= cls.INHIBITORY_SCALE

            if "interneuron" in role:
                delta *= cls.INTERNEURON_SCALE

            if "input" in role or "sensory" in role:
                delta *= cls.SENSORY_SCALE

            # Safety clamp at proposal stage
            delta = min(cls.MAX_DELTA, max(0.0, delta))

            if cls.allow_update(channel_id, delta):
                proposals[channel_id] = delta

        return proposals

    # ------------------------------------------------------------
    # Allow rules
    # ------------------------------------------------------------

    @classmethod
    def allow_update(cls, channel_id: str, delta: float) -> bool:
        """
        Decide whether a salience update is allowed.

        Rejects:
        - Near-zero noise
        - Excessively large impulses
        - Invalid channels
        """
        if abs(delta) < cls.EPSILON:
            return False

        if abs(delta) > cls.MAX_DELTA:
            return False

        if not channel_id:
            return False

        return True

    # ------------------------------------------------------------
    # Clamping
    # ------------------------------------------------------------

    @classmethod
    def clamp(cls, value: float) -> float:
        """
        Clamp salience to safe bounds.
        """
        if value > cls.MAX_ABS_SALIENCE:
            return cls.MAX_ABS_SALIENCE
        if value < -cls.MAX_ABS_SALIENCE:
            return -cls.MAX_ABS_SALIENCE
        return value
