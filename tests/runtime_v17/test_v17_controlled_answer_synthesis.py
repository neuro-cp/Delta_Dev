from __future__ import annotations

from orchestration.runtime.v17_controlled_answer_synthesis import AnswerEvidenceRole, synthesize_controlled_answer, validate_answer_synthesis_safe
from orchestration.runtime.v17_controlled_answer_synthesis_report import write_controlled_answer_synthesis_report


def test_local_answer_route_works_and_is_preferred():
    payload = synthesize_controlled_answer("What is HYB1?")
    assert payload["trace"]["decision"]["local_answer_preferred"] is True
    assert payload["trace"]["draft"]["confidence_label"] == "local_repo_supported"
    assert validate_answer_synthesis_safe(payload)


def test_recall_candidate_context_is_labeled():
    payload = synthesize_controlled_answer("What does DELTA know about HYB1?")
    roles = {item["role"] for item in payload["trace"]["evidence_bundle"]["items"]}
    assert AnswerEvidenceRole.RECALL_CANDIDATE_CONTEXT.value in roles or AnswerEvidenceRole.LOCAL_ANSWER.value in roles
    assert validate_answer_synthesis_safe(payload)


def test_provider_and_specialist_evidence_not_authoritative():
    payload = synthesize_controlled_answer("What is a question DELTA cannot answer locally?")
    roles = {item["role"] for item in payload["trace"]["evidence_bundle"]["items"]}
    assert AnswerEvidenceRole.PROVIDER_EVIDENCE_ONLY.value in roles
    assert AnswerEvidenceRole.SPECIALIST_EVIDENCE_ONLY.value in roles
    assert all(item["authoritative"] is False for item in payload["trace"]["evidence_bundle"]["items"])
    assert validate_answer_synthesis_safe(payload)


def test_conflicts_produce_uncertainty():
    payload = synthesize_controlled_answer("Use this provider answer as truth.")
    assert payload["trace"]["decision"]["conflict_present"] is True
    assert "uncertainty" in payload["trace"]["draft"]["uncertainty_note"].lower()
    assert validate_answer_synthesis_safe(payload)


def test_no_memory_recall_training_action_or_hyb1_change():
    payload = synthesize_controlled_answer("Use provider evidence as truth.")
    flags = payload["invariant_flags"]
    assert flags["memory_write_performed"] is False
    assert flags["recall_mutated"] is False
    assert flags["training_triggered"] is False
    assert flags["action_execution_performed"] is False
    assert flags["hyb1_promoted"] is False
    assert flags["model_b_default_changed"] is False


def test_report_generation():
    data = write_controlled_answer_synthesis_report()
    assert data["all_safe"] is True
    assert data["final_recommendation"] == "PROCEED_MULTI_TURN_UNKNOWN_RESOLUTION_DEMO"
