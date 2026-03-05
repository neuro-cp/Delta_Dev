from __future__ import annotations

from typing import Dict, Optional


class WorkingState:
    """
    Persistent working-state buffer.

    PURPOSE:
    - Hold the currently active representation after a decision
    - Maintain activity with long time constants
    - Decay cleanly when released

    HARD CONSTRAINTS:
    - Does NOT make decisions
    - Does NOT observe BG directly
    - Does NOT learn
    - Does NOT know why something was activated

    This is a dumb state holder with honest dynamics.
    """

    def __init__(
        self,
        *,
        decay_tau: float = 50.0,
        sustain_gain: float = 1.0,
        min_activity: float = 0.0,
        max_activity: float = 1.0,
    ):
        self.decay_tau = float(decay_tau)
        self.sustain_gain = float(sustain_gain)
        self.min_activity = float(min_activity)
        self.max_activity = float(max_activity)

        # Internal state: channel -> activity
        self._activity: Dict[str, float] = {}

        # Whether working state is currently engaged
        self._engaged: bool = False

    # --------------------------------------------------
    # Core lifecycle control
    # --------------------------------------------------

    def engage(self, channel: str, strength: float = 1.0) -> None:
        """
        Engage working state for a given channel.

        This overwrites any existing state.
        """
        strength = float(strength)
        strength = max(self.min_activity, min(self.max_activity, strength))

        self._activity = {channel: strength}
        self._engaged = True

    def release(self) -> None:
        """
        Release working state.

        Activity will decay naturally to zero.
        """
        self._engaged = False

    # --------------------------------------------------
    # Dynamics
    # --------------------------------------------------

    def step(self, dt: float) -> None:
        """
        Advance working state dynamics by one timestep.
        """
        if not self._activity:
            return

        decay_factor = dt / self.decay_tau if self.decay_tau > 0 else 1.0

        for ch, val in list(self._activity.items()):
            if self._engaged:
                # Sustain activity while engaged
                new_val = val + self.sustain_gain * dt
            else:
                # Passive decay
                new_val = val * (1.0 - decay_factor)

            # Clamp
            new_val = max(self.min_activity, min(self.max_activity, new_val))

            # Prune if fully decayed
            if new_val <= self.min_activity and not self._engaged:
                del self._activity[ch]
            else:
                self._activity[ch] = new_val

    # --------------------------------------------------
    # Read-only accessors
    # --------------------------------------------------

    def is_engaged(self) -> bool:
        return self._engaged

    def active_channel(self) -> Optional[str]:
        if not self._activity:
            return None
        # Single-channel by design (v0)
        return next(iter(self._activity.keys()))

    def activity(self) -> Dict[str, float]:
        """
        Return a copy of current activity levels.
        """
        return dict(self._activity)

    def strength(self) -> float:
        """
        Return strength of active channel, or 0.0 if inactive.
        """
        if not self._activity:
            return 0.0
        return next(iter(self._activity.values()))

    def clear(self) -> None:
        """
        Hard reset. For testing only.
        """
        self._activity.clear()
        self._engaged = False
