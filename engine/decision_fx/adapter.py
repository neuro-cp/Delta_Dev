from __future__ import annotations

from typing import Any, Dict, Optional

from engine.decision_fx.decision_policy import DecisionPolicy
from engine.decision_fx.decision_router import DecisionRouter
from engine.decision_fx.decision_effects import DecisionEffects
from engine.decision_fx.runtime_hook import DecisionRuntimeHook
from engine.decision_fx.decision_trace import DecisionTrace

from engine.execution.execution_target import ExecutionTarget


class DecisionFXAdapter:
    """
    Facade / adapter for the Decision FX subsystem.

    PURPOSE:
    - Provide a single runtime-facing entry point
    - Encapsulate policy, routing, effects, and tracing
    - Guarantee read-only, advisory behavior

    HARD GUARANTEES:
    - No learning
    - No stateful dynamics
    - No authority over decisions
    - Safe to disable at runtime
    """

    def __init__(self, *, enable_trace: bool = True, execution_gate=None):
        self.policy = DecisionPolicy()
        self.router = DecisionRouter()
        self.effects = DecisionEffects()
        self.hook = DecisionRuntimeHook()

        self.execution_gate = execution_gate  # may be None (identity)

        self.enable_trace = bool(enable_trace)
        self._trace: Optional[DecisionTrace] = (
            DecisionTrace() if self.enable_trace else None
        )

    # --------------------------------------------------
    # Runtime-facing API (SINGLE CALL)
    # --------------------------------------------------

    def apply(
        self,
        *,
        decision_state: Dict[str, Any],
        dominance: Dict[str, float],
    ) -> None:
        """
        Consume a committed decision and compute advisory effects.

        This method is PURE with respect to runtime dynamics.
        """

        # 1. Policy computation (ALWAYS allowed)
        policy = self.policy.compute(
            decision_state=decision_state,
            dominance=dominance,
        )

        # 2. Routing (ALWAYS allowed)
        routed = self.router.route(policy)

        # Normalize bundle shape
        routed.setdefault("thalamic_gain", 1.0)
        routed.setdefault("region_gain", {})
        routed.setdefault("suppress_channels", {})
        routed.setdefault("lock_action", False)

        # 3. EXECUTION GATE (bundle-level, advisory only)
        if self.execution_gate is not None:
            routed = {
                "thalamic_gain": self.execution_gate.apply(
                    target=ExecutionTarget.DECISION_FX_THALAMIC_GAIN,
                    value=float(routed.get("thalamic_gain", 1.0)),
                    identity=1.0,
                ),
                "region_gain": self.execution_gate.apply(
                    target=ExecutionTarget.DECISION_FX_REGION_GAIN,
                    value=dict(routed.get("region_gain", {})),
                    identity={},
                ),
                "suppress_channels": self.execution_gate.apply(
                    target=ExecutionTarget.DECISION_FX_SUPPRESS_CHANNELS,
                    value=dict(routed.get("suppress_channels", {})),
                    identity={},
                ),
                "lock_action": self.execution_gate.apply(
                    target=ExecutionTarget.DECISION_FX_LOCK,
                    value=bool(routed.get("lock_action", False)),
                    identity=False,
                ),
            }

        # 4. Effects application (already gated)
        effects = self.effects.apply(**routed)

        # 5. Runtime hook ingestion (unchanged)
        self.hook.ingest(effects)

        # 6. Trace (records what *would* have happened + what was gated)
        if self._trace is not None:
            self._trace.record(
                step=int(decision_state.get("step", -1)),
                time=float(decision_state.get("time", 0.0)),
                winner=decision_state.get("winner"),
                dominance=dict(dominance or {}),
                delta=float(decision_state.get("delta_dominance", 0.0)),
                relief=float(decision_state.get("relief", 0.0)),
                bias=policy.get("bias_snapshot"),
                effects=effects,
                runtime_hook=self.hook.snapshot(),
            )

    # --------------------------------------------------
    # Read-only exposure
    # --------------------------------------------------

    def get_thalamic_gain_modifier(self) -> float:
        return float(self.hook.thalamic_gain())

    def get_thalamic_gain(self) -> float:
        return float(self.hook.thalamic_gain())

    def dump(self) -> Dict[str, Any]:
        return self.hook.snapshot()
