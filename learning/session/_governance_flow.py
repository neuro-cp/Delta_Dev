from __future__ import annotations

from typing import Any, Iterable

from learning.fragility_index.fragility_engine import FragilityEngine
from learning.containment_envelope.envelope_engine import ContainmentEnvelopeEngine
from learning.calibration_application.application_engine import (
    CalibrationApplicationEngine,
)
from learning.governance_record.record_engine import GovernanceRecordEngine
from learning.governance_gate.gate_engine import GovernanceGateEngine


def run_governance_chain(
    proposals: Iterable[Any],
    report_surface: Any,
) -> Any:
    """
    Executes the full offline governance chain:

        fragility → envelope → calibration → record → gate

    CONTRACT:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    - No registry access
    - Raises AssertionError on gate rejection
    """

    # 1) Structural metric (pure)
    proposed_adjustment = sum(len(p.deltas) for p in proposals)

    # 2) Fragility
    fragility_engine = FragilityEngine()
    fragility = fragility_engine.evaluate(
        coherence=getattr(report_surface, "coherence", None),
        entropy=getattr(report_surface, "entropy", None),
        momentum=getattr(report_surface, "momentum", None),
        escalation=getattr(report_surface, "escalation", None),
    )

    # 3) Envelope
    envelope_engine = ContainmentEnvelopeEngine()
    envelope = envelope_engine.evaluate(
        fragility=fragility,
        max_adjustment=10,
    )

    allowed_adjustment = envelope.get("allowed_adjustment", 10)

    # 4) Calibration
    calibration_engine = CalibrationApplicationEngine()
    application = calibration_engine.evaluate(
        proposed_adjustment=proposed_adjustment,
        allowed_adjustment=allowed_adjustment,
    )

    # 5) Governance Record
    record_engine = GovernanceRecordEngine()
    record = record_engine.evaluate(
        fragility=fragility,
        envelope=envelope,
        application=application,
    )

    # 6) Gate
    gate_engine = GovernanceGateEngine()
    decision = gate_engine.evaluate(record=record)

    if not decision.get("approved", False):
        raise AssertionError("GovernanceGate rejected learning session.")

    return record