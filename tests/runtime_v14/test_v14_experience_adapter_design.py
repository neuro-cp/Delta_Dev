from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_experience_adapter import (
    RUNTIME_V14M_INVARIANT_FLAGS,
    ExperienceBoundaryType,
    ExperienceNormalizationOutcome,
    ExperienceSourceType,
    RawExperienceInputKind,
    create_experience_adapter_plan,
    create_experience_adapter_report_entry,
    create_experience_adapter_trace,
    create_experience_boundary,
    create_experience_record,
    create_experience_source_metadata,
    create_raw_experience_input,
    decide_experience_normalization,
    validate_experience_boundary_inert,
    validate_experience_decision_review_only,
    validate_experience_plan_inert,
    validate_experience_record_inert,
    validate_experience_report_entry_review_only,
    validate_experience_trace_review_only,
    validate_raw_experience_input_inert,
    validate_source_metadata_non_hidden,
)
from orchestration.runtime.v14_experience_report import build_experience_adapter_report_data, write_experience_adapter_report


def _raw():
    metadata = create_experience_source_metadata(source_type=ExperienceSourceType.USER_DIRECT, source_reference="user-1", provenance_notes="explicit message")
    return create_raw_experience_input(input_kind=RawExperienceInputKind.USER_MESSAGE, content="Please review the plan.", source_metadata=metadata, lane_scope=("reasoning",), provenance_reference_ids=("trace-1",))


def test_importing_experience_adapter_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)
    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14M_INVARIANT_FLAGS.values())


def test_source_metadata_and_raw_input_are_deterministic_and_inert():
    raw = _raw()
    duplicate = _raw()
    assert raw.input_id == duplicate.input_id
    assert validate_source_metadata_non_hidden(raw.source_metadata)
    assert validate_raw_experience_input_inert(raw)


def test_boundary_does_not_enable_ingestion_or_listener():
    boundary = create_experience_boundary(_raw(), boundary_type=ExperienceBoundaryType.SINGLE_MESSAGE)
    assert boundary.automatic_ingestion_enabled is False
    assert boundary.background_listener_enabled is False
    assert validate_experience_boundary_inert(boundary)


def test_experience_record_is_not_memory_canonical_or_learned():
    raw = _raw()
    boundary = create_experience_boundary(raw, boundary_type=ExperienceBoundaryType.SINGLE_MESSAGE)
    record = create_experience_record(raw, boundary, eligible_for_semantic_adapter=True)
    assert record.memory is False
    assert record.canonical is False
    assert record.learned is False
    assert record.active is False
    assert validate_experience_record_inert(record)


def test_normalization_decision_is_not_applied_and_triggers_no_training():
    raw = _raw()
    boundary = create_experience_boundary(raw, boundary_type=ExperienceBoundaryType.SINGLE_MESSAGE)
    record = create_experience_record(raw, boundary, eligible_for_semantic_adapter=True)
    decision = decide_experience_normalization(raw, record)
    assert decision.outcome == ExperienceNormalizationOutcome.ELIGIBLE_FOR_STRUCTURAL_SEMANTIC_ADAPTER
    assert validate_experience_decision_review_only(decision)


def test_trace_plan_and_entry_are_review_only():
    raw = _raw()
    boundary = create_experience_boundary(raw, boundary_type=ExperienceBoundaryType.SINGLE_MESSAGE)
    record = create_experience_record(raw, boundary)
    decision = decide_experience_normalization(raw, record)
    trace = create_experience_adapter_trace(raw, boundary, record, decision)
    plan = create_experience_adapter_plan(inputs=(raw,), records=(record,), decisions=(decision,))
    entry = create_experience_adapter_report_entry(trace, raw, boundary, record, decision)
    assert validate_experience_trace_review_only(trace)
    assert validate_experience_plan_inert(plan)
    assert validate_experience_report_entry_review_only(entry)


def test_experience_report_data_states_non_autonomous_status():
    data = build_experience_adapter_report_data()
    assert data["final_recommendation"] == "PROCEED_ACTIVE_SPECIALIST_ROUTING_DESIGN_GATED"
    assert data["safety_boundaries"]["live_ingestion_enabled"] is False
    assert data["safety_boundaries"]["background_listener_enabled"] is False
    assert data["inactive_systems"]["hidden_telemetry_capture"] is False


def test_write_experience_adapter_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14m_raw_input_experience_adapter_design.md"
    json_path = tmp_path / "runtime_v14m_raw_input_experience_adapter_design.json"
    write_experience_adapter_report(md_path, json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_ACTIVE_SPECIALIST_ROUTING_DESIGN_GATED"
    assert "raw input != memory" in text
