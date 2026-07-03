from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_semantic_adapter_report import build_semantic_adapter_report_data, write_semantic_adapter_report
from orchestration.runtime.v14_structural_semantic_adapter import (
    RUNTIME_V14L_INVARIANT_FLAGS,
    SemanticAdapterOutcome,
    SemanticFrameType,
    SemanticRoleType,
    SemanticSignalPolarity,
    SemanticSignalType,
    StructuralInputKind,
    create_semantic_adapter_plan,
    create_semantic_adapter_report_entry,
    create_semantic_adapter_trace,
    create_semantic_frame,
    create_semantic_role_assignment,
    create_semantic_signal,
    create_structural_input_unit,
    decide_semantic_adapter,
    validate_semantic_adapter_decision_review_only,
    validate_semantic_adapter_plan_inert,
    validate_semantic_adapter_report_entry_review_only,
    validate_semantic_adapter_trace_review_only,
    validate_semantic_frame_inert,
    validate_semantic_role_assignment_non_authoritative,
    validate_semantic_signal_inert,
    validate_structural_input_unit_inert,
)


def _unit():
    return create_structural_input_unit(
        source_reference_id="msg-1",
        input_kind=StructuralInputKind.USER_MESSAGE,
        raw_text="The pump failed after maintenance.",
        structured_fields={"subject": "pump", "event": "failed"},
        source_metadata={"source": "test"},
        lane_scope=("reasoning",),
        provenance_reference_ids=("trace-1",),
    )


def _frame():
    return create_semantic_frame(
        unit=_unit(),
        frame_type=SemanticFrameType.CLAIM,
        normalized_summary="Pump failure occurred after maintenance.",
        entity_references=("pump",),
        claim_references=("failure-after-maintenance",),
    )


def test_importing_semantic_adapter_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14L_INVARIANT_FLAGS.values())


def test_structural_input_unit_is_deterministic_not_memory_or_training():
    unit = _unit()
    duplicate = _unit()
    assert unit.unit_id == duplicate.unit_id
    assert unit.active is False
    assert unit.memory is False
    assert unit.training_example is False
    assert validate_structural_input_unit_inert(unit)


def test_semantic_frame_is_inactive_noncanonical_not_learned():
    frame = _frame()
    duplicate = _frame()
    assert frame.frame_id == duplicate.frame_id
    assert frame.active is False
    assert frame.canonical is False
    assert frame.learned is False
    assert validate_semantic_frame_inert(frame)


def test_role_assignment_is_non_authoritative_and_not_applied():
    role = create_semantic_role_assignment(
        frame=_frame(),
        target_reference="failure-after-maintenance",
        role_type=SemanticRoleType.USER_CLAIM,
        confidence_state=1.2,
    )
    assert role.normalized_confidence() == 1.0
    assert role.authoritative is False
    assert role.applied is False
    assert validate_semantic_role_assignment_non_authoritative(role)


def test_semantic_signal_is_inactive_and_not_applied():
    signal = create_semantic_signal(
        frame=_frame(),
        signal_type=SemanticSignalType.POSSIBLE_MEMORY_CANDIDATE,
        polarity=SemanticSignalPolarity.SUPPORTS_ADAPTATION,
        severity_or_weight=0.8,
    )
    assert signal.active is False
    assert signal.applied is False
    assert validate_semantic_signal_inert(signal)


def test_semantic_adapter_decision_is_review_only_and_non_mutating():
    unit = _unit()
    frame = _frame()
    signal = create_semantic_signal(
        frame=frame,
        signal_type=SemanticSignalType.POSSIBLE_MEMORY_CANDIDATE,
        polarity=SemanticSignalPolarity.SUPPORTS_ADAPTATION,
    )
    decision = decide_semantic_adapter(unit, frames=(frame,), signals=(signal,))
    assert decision.outcome == SemanticAdapterOutcome.ELIGIBLE_FOR_FUTURE_CANDIDATE_ENVELOPE
    assert decision.applied is False
    assert decision.memory_written is False
    assert decision.training_triggered is False
    assert validate_semantic_adapter_decision_review_only(decision)


def test_trace_plan_and_report_entry_are_inert():
    unit = _unit()
    frame = _frame()
    role = create_semantic_role_assignment(frame=frame, target_reference="pump", role_type=SemanticRoleType.EVIDENCE_SOURCE)
    signal = create_semantic_signal(frame=frame, signal_type=SemanticSignalType.POSSIBLE_FEEDBACK, polarity=SemanticSignalPolarity.NEUTRAL)
    decision = decide_semantic_adapter(unit, frames=(frame,), signals=(signal,))
    trace = create_semantic_adapter_trace(unit=unit, frames=(frame,), role_assignments=(role,), signals=(signal,), decision=decision)
    plan = create_semantic_adapter_plan(units=(unit,), frames=(frame,), decisions=(decision,))
    entry = create_semantic_adapter_report_entry(trace=trace, frames=(frame,), role_assignments=(role,), signals=(signal,), decision=decision)
    assert validate_semantic_adapter_trace_review_only(trace)
    assert validate_semantic_adapter_plan_inert(plan)
    assert validate_semantic_adapter_report_entry_review_only(entry)


def test_semantic_adapter_report_data_states_design_only_status():
    data = build_semantic_adapter_report_data()
    assert data["final_recommendation"] == "PROCEED_RAW_INPUT_EXPERIENCE_ADAPTER_DESIGN"
    assert data["safety_boundaries"]["semantic_adapter_enabled"] is False
    assert data["safety_boundaries"]["candidate_envelope_write_enabled"] is False
    assert data["inactive_systems"]["candidate_envelope_write"] is False


def test_write_semantic_adapter_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14l_structural_semantic_adapter_design.md"
    json_path = tmp_path / "runtime_v14l_structural_semantic_adapter_design.json"
    write_semantic_adapter_report(md_path, json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_RAW_INPUT_EXPERIENCE_ADAPTER_DESIGN"
    assert "semantic frame != memory" in text
