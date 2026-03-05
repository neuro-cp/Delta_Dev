# engine/cognition/audit/tests/test_hypothesis_audit_runner_basic.py
from __future__ import annotations

from engine.cognition.hypothesis_registry import HypothesisRegistry
from engine.cognition.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis_bias import HypothesisBias

from engine.cognition.audit.hypothesis_audit_trace import HypothesisAuditTrace
from engine.cognition.audit.hypothesis_audit_runner import HypothesisAuditRunner


def test_hypothesis_audit_runner_records_failure_modes() -> None:
    """
    Phase-6 audit invariant:

    Even when:
      - no hypothesis stabilizes
      - no bias is produced

    The audit layer MUST:
      - record explanatory events
      - never be silent
    """

    # --------------------------------------------------
    # Minimal cognition stack (offline)
    # --------------------------------------------------

    registry = HypothesisRegistry()
    h0 = registry.create(hypothesis_id="H0", created_step=0)
    h1 = registry.create(hypothesis_id="H1", created_step=0)

    # Deliberately sub-threshold activations
    h0.activation = 0.02
    h1.activation = 0.01

    stabilizer = HypothesisStabilization(
        activation_threshold=0.10,
        sustain_steps=5,
    )

    biaser = HypothesisBias(
        bias_gain=0.05,
        max_bias=0.2,
    )

    trace = HypothesisAuditTrace()

    runner = HypothesisAuditRunner(
        registry=registry,
        stabilizer=stabilizer,
        biaser=biaser,
        trace=trace,
    )

    # --------------------------------------------------
    # Simulate a few offline cognition steps
    # --------------------------------------------------

    for step in range(6):
        registry.tick()

        # Observe hypothesis state
        runner.audit_step(step=step)

        # Stabilization attempt (expected to fail)
        events = stabilizer.step(registry.all())
        runner.audit_stabilization(step=step, stabilization_events=events)

        # Bias attempt (expected to be skipped)
        runner.audit_bias(step=step)

    # --------------------------------------------------
    # Assertions: audit must explain failure
    # --------------------------------------------------

    events = trace.events
    assert events, "Audit trace is empty (silent cognition is forbidden)"

    event_types = {e.event for e in events}

    # Core failure explanations we REQUIRE
    assert "hypothesis_state" in event_types
    assert "no_hypothesis_stabilized" in event_types
    assert "bias_skipped_no_stabilized_hypotheses" in event_types

    # Sanity check: no stabilization should occur
    assert "hypothesis_stabilized" not in event_types
