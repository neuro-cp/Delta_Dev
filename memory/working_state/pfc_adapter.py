from __future__ import annotations

from typing import Any, Dict, Optional, Callable

from memory.working_state.working_state import WorkingState
from memory.working_state.working_policy import WorkingPolicy
from memory.working_state.working_hook import WorkingRuntimeHook


class PFCAdapter:
    """
    Adapter / facade for PFC-like Working State.

    PURPOSE:
    - Integrate post-decision working state into the runtime
    - Bridge decision latch → working memory dynamics
    - Expose advisory stabilization signals

    DESIGN GUARANTEES:
    - Read-only with respect to decision arbitration
    - No learning
    - No authority over BG
    - Safe to disable at runtime
    """

    def __init__(
        self,
        *,
        enable: bool = True,
        state: Optional[WorkingState] = None,
        policy: Optional[WorkingPolicy] = None,
    ):
        self.enable = bool(enable)

        self._hook = WorkingRuntimeHook(
            state=state or WorkingState(),
            policy=policy or WorkingPolicy(),
        )

        # Ephemeral external modulation (cleared every step)
        self._external_gain_fn: Optional[Callable[[float], float]] = None

    # --------------------------------------------------
    # Runtime-facing API
    # --------------------------------------------------

    def ingest_decision(self, decision_state: Optional[Dict[str, Any]]) -> None:
        """
        Ingest decision latch output.

        Called AFTER latch evaluation.
        """
        if not self.enable or decision_state is None:
            return

        self._hook.ingest(decision_state=decision_state)

    def step(self, dt: float) -> None:
        """
        Advance working-state dynamics.

        Order:
        1. Internal dynamics
        2. One-shot external modulation (if present)
        """
        if not self.enable:
            return

        # 1. Internal working-state dynamics
        self._hook.step(dt)

        # 2. Ephemeral external gain modulation (one-step only)
        if self._external_gain_fn is not None:
            try:
                base = self._hook.strength()
                mod = float(self._external_gain_fn(base))

                # Safety clamp: never negative
                mod = max(0.0, mod)

                # IMPORTANT:
                # Mutate hook-owned state directly.
                # This preserves encapsulation and avoids new authority APIs.
                self._hook.state._strength = mod
            finally:
                self._external_gain_fn = None

    # --------------------------------------------------
    # External modulation hooks (ephemeral)
    # --------------------------------------------------

    def apply_external_gain(self, fn: Callable[[float], float]) -> None:
        """
        Apply a temporary external modifier to working-state strength.

        - fn: Callable[[float], float]
        - Applied after internal dynamics
        - Cleared automatically after one step
        """
        if not self.enable:
            return

        self._external_gain_fn = fn

    # --------------------------------------------------
    # Advisory outputs (read-only)
    # --------------------------------------------------

    def is_engaged(self) -> bool:
        return self._hook.is_engaged() if self.enable else False

    def active_channel(self) -> Optional[str]:
        return self._hook.active_channel() if self.enable else None

    def strength(self) -> float:
        return self._hook.strength() if self.enable else 0.0

    def suppressive_bias(self) -> Dict[str, float]:
        """
        Advisory suppressive bias hint.

        Intended for:
        - BG competition dampening
        - attention narrowing
        - post-decision stabilization

        NOT applied automatically.
        """
        return self._hook.suppressive_bias() if self.enable else {}

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        if not self.enable:
            return {
                "enabled": False,
                "engaged": False,
            }

        snap = self._hook.snapshot()
        snap["enabled"] = True
        return snap

    def reset(self) -> None:
        """
        Hard reset. For testing only.
        """
        self._hook.reset()
        self._external_gain_fn = None
