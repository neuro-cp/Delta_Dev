# engine/cognition/audit/tests/test_hypothesis_audit_stabilization_success.py
from __future__ import annotations

from typing import List

from engine.cognition.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis_grounding import HypothesisGrounding
from engine.cognition.hypothesis_dynamics import HypothesisDynamics
from engine.cognition.hypothesis_competition import HypothesisCompetition
from engine.cognition.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis_bias import HypothesisBias


class _ConstantObservedAssembly:
    """
    Test-only stand-in for an observed assembly.

    Always returns a fixed positive signal to guarantee support accumulation.
    """
    def __init__(self, value: float) -> None:
        self._value = float(value)

    def output(self) -> float:
        return self._value


def test_hypothesis_audit_stabilization_success() -> None:
    """
    Forced-success calibration test.

    Guarantees:
    - hypothesis receives sustained support
    - activation crosses stabilization threshold
    - stabilization event fires
    - bias is produced

    This test MUST pass for Phase 6 to be considered structurally correct.
    """

    # --------------------------------------------------
    # Registry & hypothesis
    # --------------------------------------------------
    reg = HypothesisRegistry()
    h = reg.create(hypothesis_id="H_TEST", created_step=0)

    # Start below threshold but active
    h.activation = 0.05

    # --------------------------------------------------
    # Cognition components (conservative settings)
    # --------------------------------------------------
    grounding = HypothesisGrounding(
        support_gain=1.0,
        max_support=10.0,
    )

    dynamics = HypothesisDynamics(
        decay_rate=0.0,  # no decay for calibration
    )

    competition = HypothesisCompetition(
        competition_gain=0.0,  # single hypothesis, no suppression
    )

    stabilizer = HypothesisStabilization(
        activation_threshold=0.10,
        sustain_steps=3,
    )

    biaser = HypothesisBias(
        bias_gain=0.1,
        max_bias=0.5,
    )

    # --------------------------------------------------
    # Constant observed signal
    # --------------------------------------------------
    observed: List[_ConstantObservedAssembly] = [
        _ConstantObservedAssembly(value=1.0)
    ]

    stabilized_events = []

    # --------------------------------------------------
    # Step loop (offline cognition tick)
    # --------------------------------------------------
    for step in range(10):
        reg.tick()

        grounding.step(
            hypotheses=reg.all(),
            observed_assemblies=observed,
        )

        # TEST-ONLY activation mapping (support → activation)
        for h in reg.all():
            if h.active:
                h.activation = min(1.0, h.support / grounding.max_support)

        dynamics.step(reg.all())
        competition.step(reg.all())

        events = stabilizer.step(reg.all())
        stabilized_events.extend(events)

        if stabilized_events:
            break

    # --------------------------------------------------
    # Assertions: stabilization
    # --------------------------------------------------
    assert stabilized_events, "Expected hypothesis to stabilize but no events fired"

    event = stabilized_events[0]
    assert event["event"] == "hypothesis_stabilized"
    assert event["hypothesis_id"] == "H_TEST"

    stabilized = [h for h in reg.all() if h.active]
    assert stabilized, "Stabilized hypothesis is not active"

    # --------------------------------------------------
    # Assertions: bias
    # --------------------------------------------------
    bias = biaser.compute_bias(stabilized_hypotheses=stabilized)

    assert "H_TEST" in bias
    assert 0.0 < bias["H_TEST"] <= biaser.max_bias
