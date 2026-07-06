from orchestration.runtime.ov3_controlled_reasoning_vertical_slice import (
    OV3_QUESTIONS,
    answer_ov3_question,
    answer_vertical_question,
    is_ov3_question,
    run_ov3_vertical_slice,
    score_reasoning_answer,
    write_ov3_reports,
)
from orchestration.runtime.ov1_operational_validation import extract_semantic_objects, load_allowlisted_corpus
from orchestration.runtime.ov2_cognitive_quality import build_proposition_layer, generate_hypotheses


def test_ov3_runs_complete_vertical_workflow_without_live_activation():
    payload = run_ov3_vertical_slice()
    assert payload["workflow"][0] == "fixture corpus"
    assert payload["workflow"][-1] == "operator recommendation"
    assert payload["safety"]["provider_call_performed"] is False
    assert payload["safety"]["training_performed"] is False
    assert payload["safety"]["canonical_write_performed"] is False
    assert payload["safety"]["activation_performed"] is False


def test_ov3_answers_all_required_questions_with_reasoning_fields():
    payload = run_ov3_vertical_slice()
    assert len(payload["answers"]) == len(OV3_QUESTIONS)
    for answer in payload["answers"]:
        assert answer["known_claims"]
        assert answer["inferred_relationships"]
        assert answer["contradictions"]
        assert answer["missing_evidence"]
        assert answer["disconfirming_evidence"]
        assert answer["unsupported_conclusions_refused"]
        assert answer["provenance_ids"]
        assert answer["reasoning_path"]


def test_ov3_quality_gates_reject_retrieval_summary_only_shape():
    objects = extract_semantic_objects(load_allowlisted_corpus())
    propositions = build_proposition_layer(objects)
    hypotheses = generate_hypotheses(propositions)
    answer = answer_vertical_question(OV3_QUESTIONS[0], propositions, hypotheses)
    gate = score_reasoning_answer(answer)
    assert gate["passed"] is True
    assert gate["retrieved_text_summary_only"] is False
    assert gate["average_score"] >= 0.85


def test_ov3_deduplicates_scaled_fixture_evidence():
    payload = run_ov3_vertical_slice()
    assert payload["document_count"] == 100
    assert payload["deduplication"]["deduplicated_records"] > 0
    assert payload["deduplication"]["confidence_inflation_prevented"] is True


def test_ov3_activation_eligibility_updates_only_readonly_candidates():
    payload = run_ov3_vertical_slice()
    review = payload["activation_eligibility_review"]
    assert review["activation_performed"] is False
    assert review["closest_capability_to_activation"] == "evaluation/regression loop"
    assert set(review["activation_eligible_after_manual_review"]) == {
        "read-only substrate retrieval",
        "grounded answer synthesis",
        "evaluation/regression loop",
    }


def test_ov3_local_answer_routes_required_questions():
    assert is_ov3_question("Run OV3 vertical slice")
    result = answer_ov3_question("Which capabilities are closest to activation?")
    assert result["phase"] == "OV3 Controlled Reasoning Vertical Slice"
    assert "evaluation/regression loop" in result["answer_text"]
    assert result["safety"]["provider_call_performed"] is False


def test_ov3_reports_are_written():
    payload = write_ov3_reports()
    assert payload["reasoning_quality_score"] >= 0.85
    assert payload["final_recommendation"] == "PROCEED_OV4_OPERATOR_REVIEWED_READONLY_ACTIVATION_TRIAL"
