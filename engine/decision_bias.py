from __future__ import annotations

from typing import Dict, Optional

from engine.execution.execution_target import ExecutionTarget


class DecisionBias:
    """
    Ephemeral downstream bias applied *after* a decision is committed.

    PURPOSE:
    - Bias future signal routing in favor of a committed decision
    - Introduce short-term inertia without learning
    - Decay cleanly back to neutrality

    HARD CONSTRAINTS:
    - Read-only with respect to competition and salience
    - No learning
    - No history beyond current bias values
    - Deterministic decay
    """

    def __init__(
        self,
        *,
        decay_tau: float = 4.0,
        max_bias: float = 0.30,
        suppress_gain: float = 0.15,
        execution_gate=None,
    ):
        self.decay_tau = float(decay_tau)
        self.max_bias = float(max_bias)
        self.suppress_gain = float(suppress_gain)

        # channel_id -> bias value
        self._bias: Dict[str, float] = {}

        # Diagnostics
        self.last_winner: Optional[str] = None
        self.last_applied_step: Optional[int] = None

        # Ephemeral external bias modifiers (cleared every step)
        self._external_modifiers = []

        # Optional execution gate (identity if None)
        self.execution_gate = execution_gate

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def apply_decision(
        self,
        *,
        winner: str,
        channels: Optional[list[str]] = None,
        strength: float = 1.0,
        step: Optional[int] = None,
    ) -> None:
        strength = max(0.0, min(1.0, float(strength)))

        win_bias = min(self.max_bias, self.max_bias * strength)
        self._bias[winner] = win_bias

        if channels:
            for ch in channels:
                if ch == winner:
                    continue
                self._bias[ch] = max(
                    -self.max_bias,
                    -self.suppress_gain * win_bias,
                )

        self.last_winner = winner
        self.last_applied_step = step

    def get(self, channel_id: str) -> float:
        """
        Return current bias for a channel (execution-gated).
        """
        value = float(self._bias.get(channel_id, 0.0))

        if self.execution_gate is not None:
            value = float(
                self.execution_gate.apply(
                    target=ExecutionTarget.DECISION_BIAS,
                    value=value,
                    identity=0.0,
                )
            )

        return value

    # ------------------------------------------------------------
    # External modulation hooks (ephemeral)
    # ------------------------------------------------------------

    def apply_external(self, fn) -> None:
        """
        Apply a temporary external modifier to the bias map.

        - fn: Callable[[Dict[str, float]], Dict[str, float]]
        - Applied after decay
        - Cleared automatically after one step
        """
        self._external_modifiers.append(fn)

    # ------------------------------------------------------------
    # Decay + execution gating
    # ------------------------------------------------------------

    def step(self, dt: float) -> None:
        if self.decay_tau <= 0:
            self._bias.clear()
        else:
            decay = float(dt) / self.decay_tau
            for ch in list(self._bias.keys()):
                v = self._bias[ch] * (1.0 - decay)
                if abs(v) <= 1e-6:
                    del self._bias[ch]
                else:
                    self._bias[ch] = v

        # --------------------------------------------------
        # Apply ephemeral external modifiers
        # --------------------------------------------------
        if self._external_modifiers:
            bias = dict(self._bias)

            for fn in self._external_modifiers:
                bias = fn(bias)

            self._external_modifiers.clear()

            self._bias = bias

        # --------------------------------------------------
        # Execution gate (FINAL, per-channel)
        # --------------------------------------------------
        if self.execution_gate is not None:
            gated: Dict[str, float] = {}

            for ch, v in self._bias.items():
                gv = float(
                    self.execution_gate.apply(
                        target=ExecutionTarget.DECISION_BIAS,
                        value=v,
                        identity=0.0,
                    )
                )

                if abs(gv) > 1e-6:
                    gated[ch] = max(-self.max_bias, min(self.max_bias, gv))

            self._bias = gated

    # ------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------

    def dump(self) -> Dict[str, float]:
        return dict(self._bias)
