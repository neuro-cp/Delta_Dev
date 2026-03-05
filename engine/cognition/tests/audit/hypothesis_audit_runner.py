# engine/cognition/audit/hypothesis_audit_runner.py
from __future__ import annotations

from typing import Any, Iterable, List

from engine.cognition.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis_bias import HypothesisBias

from .hypothesis_audit_event import HypothesisAuditEvent
from .hypothesis_audit_trace import HypothesisAuditTrace


class HypothesisAuditRunner:
    """
    Offline audit runner for Phase-6 cognition.

    Responsibilities:
    - Observe hypothesis state over time
    - Record *why* nothing stabilized when applicable
    - Record bias computation outcomes

    Explicitly does NOT:
    - modify hypotheses
    - inject bias
    - influence runtime or replay
    """

    def __init__(
        self,
        *,
        registry: HypothesisRegistry,
        stabilizer: HypothesisStabilization,
        biaser: HypothesisBias,
        trace: HypothesisAuditTrace,
    ) -> None:
        self.registry = registry
        self.stabilizer = stabilizer
        self.biaser = biaser
        self.trace = trace

    # --------------------------------------------------
    # Per-step audit
    # --------------------------------------------------

    def audit_step(self, *, step: int) -> None:
        """
        Observe hypotheses at a single cognition step.
        """
        active = [h for h in self.registry.all() if h.active]

        if not active:
            self.trace.append(
                HypothesisAuditEvent(
                    event="no_active_hypotheses",
                    step=step,
                )
            )
            return

        for h in active:
            self.trace.append(
                HypothesisAuditEvent(
                    event="hypothesis_state",
                    step=step,
                    hypothesis_id=h.hypothesis_id,
                    details={
                        "activation": float(getattr(h, "activation", 0.0)),
                        "support": float(getattr(h, "support", 0.0)),
                    },
                )
            )

    # --------------------------------------------------
    # Stabilization audit
    # --------------------------------------------------

    def audit_stabilization(
        self,
        *,
        step: int,
        stabilization_events: Iterable[dict],
    ) -> None:
        """
        Record stabilization outcomes from HypothesisStabilization.
        """
        events = list(stabilization_events)

        if not events:
            self.trace.append(
                HypothesisAuditEvent(
                    event="no_hypothesis_stabilized",
                    step=step,
                )
            )
            return

        for e in events:
            self.trace.append(
                HypothesisAuditEvent(
                    event="hypothesis_stabilized",
                    step=step,
                    hypothesis_id=str(e.get("hypothesis_id")),
                    details=e,
                )
            )

    # --------------------------------------------------
    # Bias audit
    # --------------------------------------------------

    def audit_bias(self, *, step: int) -> None:
        """
        Observe bias computation without applying it.
        """
        stabilized = [
            h for h in self.registry.all()
            if h.active and getattr(h, "stabilized", False)
        ]

        if not stabilized:
            self.trace.append(
                HypothesisAuditEvent(
                    event="bias_skipped_no_stabilized_hypotheses",
                    step=step,
                )
            )
            return

        bias = self.biaser.compute_bias(stabilized_hypotheses=stabilized)

        if not bias:
            self.trace.append(
                HypothesisAuditEvent(
                    event="bias_empty",
                    step=step,
                )
            )
            return

        for hid, val in bias.items():
            self.trace.append(
                HypothesisAuditEvent(
                    event="bias_computed",
                    step=step,
                    hypothesis_id=str(hid),
                    details={"bias": float(val)},
                )
            )
