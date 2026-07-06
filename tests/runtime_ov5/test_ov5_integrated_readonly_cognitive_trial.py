from __future__ import annotations

from orchestration.runtime.ov5_integrated_readonly_cognitive_trial import (
    OV5_QUESTIONS,
    answer_ov5_question,
    is_ov5_question,
    run_ov5_integrated_trial,
    write_ov5_reports,
)


def test_ov5_runs_complete_integrated_readonly_workflow():
    payload = run_ov5_integrated_trial()

    assert payload["workflow"][0] == "fixture corpus"
    assert payload["workflow"][-1] == "operator recommendation"
    assert payload["read_only_evaluation_loop"]["execution_mode"] == "read_only_trial"
    assert payload["read_only_evaluation_loop"]["mutation_performed"] is False


def test_ov5_answers_all_required_questions_with_integrity_fields():
    payload = run_ov5_integrated_trial()

    assert len(payload["answers"]) == len(OV5_QUESTIONS)
    for answer in payload["answers"]:
        assert answer["known_claims"]
        assert answer["inferred_relationships"]
        assert answer["hypotheses"]
        assert answer["disconfirming_evidence"]
        assert answer["contradictions"]
        assert answer["missing_evidence"]
        assert answer["unsupported_conclusions_refused"]
        assert answer["provenance_ids"]
        assert answer["reasoning_path"]
        assert answer["audit_path"]
        assert answer["operator_recommendation"]


def test_ov5_cognitive_integrity_is_independent_and_passes():
    payload = run_ov5_integrated_trial()
    integrity = payload["cognitive_integrity"]

    assert integrity["retrieval_independent"] is True
    assert integrity["score"] >= 0.9
    assert integrity["passed"] is True
    assert "conclusion_consistency" in integrity["dimensions"]
    assert "audit_completeness" in integrity["dimensions"]


def test_ov5_activation_audit_preserves_governance_and_blocks_live_paths():
    payload = run_ov5_integrated_trial()
    audit = payload["activation_audit"]

    assert audit["governance_preserved"] is True
    assert audit["mutation_occurred"] is False
    assert audit["operator_signoff_required"] is True
    assert audit["participating_capabilities"]["evaluation/regression loop"] == "read_only_trial"
    assert audit["blocked_capabilities"]["training"] == "blocked"


def test_ov5_safety_invariants_remain_disabled():
    payload = run_ov5_integrated_trial()
    safety = payload["safety"]

    assert safety["provider_call_performed"] is False
    assert safety["training_performed"] is False
    assert safety["canonical_write_performed"] is False
    assert safety["memory_mutation_performed"] is False
    assert safety["live_knowledge_mutation_performed"] is False
    assert safety["scheduler_started"] is False
    assert safety["action_execution_performed"] is False
    assert safety["hyb1_promoted"] is False


def test_ov5_local_answer_routes_required_questions():
    assert is_ov5_question("Run OV5 integrated trial")
    answer = answer_ov5_question("What is cognitive integrity?")

    assert answer["phase"] == "OV5 Integrated Read-Only Cognitive Runtime Trial"
    assert "Cognitive integrity" in answer["answer_text"]
    assert answer["safety"]["provider_call_performed"] is False


def test_ov5_reports_are_written():
    payload = write_ov5_reports()

    assert payload["final_recommendation"] == "PROCEED_OV6_READONLY_RETRIEVAL_SYNTHESIS_EXPANSION"
    assert payload["cognitive_integrity"]["passed"] is True
