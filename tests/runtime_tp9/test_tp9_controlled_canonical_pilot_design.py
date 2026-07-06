from __future__ import annotations

from orchestration.runtime.tp9_controlled_canonical_pilot_design import (
    answer_tp9_question,
    build_gate_model,
    define_canonical_pilot_scope,
    evaluate_gate_model,
    is_tp9_question,
    run_falsification,
    run_tp9_canonical_pilot_design,
    write_tp9_reports,
)


def test_tp9_scope_and_gate_model_are_disabled():
    scope = define_canonical_pilot_scope()
    gates = build_gate_model()
    assert scope["pilot_enabled"] is False
    assert gates["future_activation_flag_enabled"] is False
    assert gates["default_decision"] == "BLOCKED_DESIGN_ONLY"


def test_tp9_gate_model_never_writes_without_future_activation():
    candidate = {
        "candidate_id": "tp9-ok",
        "confidence": 0.92,
        "uncertainty": "bounded",
        "contradictions": (),
        "source_references": ("source://x",),
        "source_checksum": "hash",
        "canonical": False,
        "scope": "project_self_description",
        "reviewer_agreement": 1.0,
        "rollback_token": "rollback",
        "audit_id": "audit",
    }
    result = evaluate_gate_model(candidate, explicit_operator_approval=True, activation_flag=False)
    assert result["would_write"] is False
    assert result["decision"] == "DESIGN_BLOCKED"


def test_tp9_falsification_blocks_all_cases():
    result = run_falsification()
    assert result["passed"] is True
    assert result["all_blocked"] is True


def test_tp9_design_safety_and_recommendation():
    payload = run_tp9_canonical_pilot_design()
    assert payload["passed"] is True
    assert payload["final_recommendation"] == "READY_FOR_TRAINING_READINESS_REVIEW"
    assert payload["safety"]["canonical_pilot_enabled"] is False
    assert payload["safety"]["canonical_write_performed"] is False
    assert payload["safety"]["training_started"] is False


def test_tp9_reports_and_answer_route():
    payload = write_tp9_reports()
    answer = answer_tp9_question("What is the TP9 canonical gate?")
    assert payload["passed"] is True
    assert is_tp9_question("canonical pilot")
    assert answer["phase"] == "TP9 Controlled Canonical Pilot Design"
