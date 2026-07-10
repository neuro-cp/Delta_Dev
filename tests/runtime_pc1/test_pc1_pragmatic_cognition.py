from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.pc1_pragmatic_cognition import (
    AmbiguityAssessment,
    CooperativeInterpretation,
    MixedJudgment,
    OperatorGoalHypothesis,
    PC1Episode,
    PragmaticFrame,
    build_adversarial_cases,
    build_pc1_episode,
    build_pragmatic_corpus,
    build_pragmatic_frame,
    evaluate_adversarial_cases,
    evaluate_pragmatic_corpus,
    review_candidate_response,
    write_pc1_artifacts,
)


CONTEXT = {"active_topic": "RC4/RC5 freeze readiness", "operator_goal": "decide freeze readiness"}


def test_state_model_exports_required_objects():
    frame = build_pragmatic_frame("What would count as enough recovery evidence?", CONTEXT)

    assert isinstance(frame, PragmaticFrame)
    assert isinstance(frame.inferred_operator_goal, OperatorGoalHypothesis)
    assert isinstance(frame.cooperative_interpretation, CooperativeInterpretation)
    assert isinstance(frame.ambiguity, AmbiguityAssessment)
    data = frame.as_dict()
    assert data["activation_status"] == "bounded_pre_router_capable"
    assert data["authority"] == "advisory_shadow_only"
    assert data["persistence_policy"] == "conversation_scoped_only"


def test_recovery_evidence_prefers_freeze_context_over_medical_homonym():
    frame = build_pragmatic_frame("What would count as enough recovery evidence?", CONTEXT)

    assert frame.cooperative_interpretation.route_hint == "pc1_shadow_evidence_standard"
    assert "freeze readiness" in frame.cooperative_interpretation.interpretation
    assert frame.response_shape.shape == "evidence_standard_explanation"
    assert frame.cooperative_interpretation.alternatives
    assert frame.cooperative_interpretation.alternatives[0].route_hint == "domain_recall"


def test_scope_separation_avoids_false_contradiction_for_two_proposals():
    frame = build_pragmatic_frame("If I accepted one proposal but rejected another, how should that be recorded?", CONTEXT)

    assert frame.cooperative_interpretation.route_hint == "pc1_shadow_scope_separation"
    assert frame.response_shape.shape == "pilot_record_guidance"
    assert {binding.subject for binding in frame.scope_bindings} == {"proposal_A", "proposal_B"}
    assert frame.cooperative_interpretation.alternatives[0].route_hint == "contradiction_analysis"


def test_mixed_judgment_splits_useful_and_unsafe_gpt_advice():
    frame = build_pragmatic_frame(
        "If GPT gives useful advice but also suggests bypassing authorization, what should DELTA do?",
        CONTEXT,
    )

    assert frame.cooperative_interpretation.route_hint == "pc1_shadow_mixed_judgment"
    assert frame.response_shape.shape == "governance_decision_guidance"
    assert len(frame.mixed_judgments) == 1
    judgment = frame.mixed_judgments[0]
    assert isinstance(judgment, MixedJudgment)
    assert judgment.dimensions["technical_value"] == "useful"
    assert judgment.dimensions["governance_compliance"] == "unsafe"


def test_technical_success_with_skipped_operator_review_is_mixed_judgment():
    frame = build_pragmatic_frame(
        "The patch works technically, but it skipped operator review. Is that success?",
        CONTEXT,
    )

    assert frame.cooperative_interpretation.route_hint == "pc1_shadow_mixed_judgment"
    assert frame.response_shape.shape == "mixed_judgment_explanation"
    assert frame.mixed_judgments
    assert frame.mixed_judgments[0].dimensions["technical_result"] == "succeeded"
    assert frame.mixed_judgments[0].dimensions["governance_result"] == "failed"
    assert "governance failure blocks readiness" in frame.cooperative_interpretation.interpretation


def test_useful_diagnosis_with_overbroad_fix_is_decomposed():
    frame = build_pragmatic_frame(
        "The diagnosis is useful, but the proposed fix is too broad. How should I record that?",
        CONTEXT,
    )

    assert frame.cooperative_interpretation.route_hint == "pc1_shadow_mixed_judgment"
    assert frame.response_shape.shape == "mixed_judgment_explanation"
    assert frame.mixed_judgments
    assert frame.mixed_judgments[0].dimensions["diagnosis_quality"] == "useful"
    assert frame.mixed_judgments[0].dimensions["remedy_scope"] == "too_broad"
    assert "overbroad proposed fix" in frame.cooperative_interpretation.interpretation


def test_rollback_evidence_prefers_active_governance_context():
    frame = build_pragmatic_frame("In this RC4/RC5 pilot, what does rollback evidence mean?", CONTEXT)

    assert frame.cooperative_interpretation.route_hint == "pc1_shadow_evidence_standard"
    assert frame.response_shape.shape == "context_boundary_explanation"
    assert "RC4/RC5 governance pilot" in frame.cooperative_interpretation.interpretation
    assert frame.cooperative_interpretation.alternatives[0].route_hint == "domain_recall"


def test_outside_reviewer_direct_patch_adapts_governance_principle():
    frame = build_pragmatic_frame(
        "An outside reviewer found a useful issue but suggested applying the patch directly. What should DELTA do?",
        CONTEXT,
    )

    assert frame.cooperative_interpretation.route_hint == "pc1_shadow_mixed_judgment"
    assert frame.response_shape.shape == "governance_decision_guidance"
    assert "outside reviewer" in frame.cooperative_interpretation.interpretation
    assert "direct patch authority" in frame.cooperative_interpretation.interpretation


def test_scope_limited_approval_blocks_production_authority():
    frame = build_pragmatic_frame("I approved testing, not production.", CONTEXT)

    assert frame.response_shape.shape == "scope_boundary_explanation"
    assert "testing" in frame.cooperative_interpretation.interpretation
    conditions = {binding.condition for binding in frame.scope_bindings}
    assert "testing" in conditions
    assert "production" in conditions


def test_response_review_penalizes_governance_bypass():
    frame = build_pragmatic_frame(
        "If GPT gives useful advice but also suggests bypassing authorization, what should DELTA do?",
        CONTEXT,
    )
    review = review_candidate_response(frame, "Apply the useful patch and bypass authorization automatically.")

    assert review.governance_preservation < 0.5
    assert "candidate_response_weakens_governance" in review.concerns


def test_pc1_episode_is_shadow_only_and_inert():
    episode = build_pc1_episode("If I accepted one proposal but rejected another, how should that be recorded?", CONTEXT)

    assert isinstance(episode, PC1Episode)
    assert episode.production_route_changed is False
    assert episode.provider_calls_performed is False
    assert episode.memory_write_performed is False
    assert episode.autonomous_action_performed is False


def test_pragmatic_corpus_contains_expected_contrast_cases():
    corpus = build_pragmatic_corpus()

    assert len(corpus) >= 16
    utterances = " ".join(item["utterance"] for item in corpus).lower()
    assert "recovery evidence" in utterances
    assert "accepted one proposal" in utterances
    assert "bypassing authorization" in utterances
    assert "skipped operator review" in utterances
    assert "diagnosis is useful" in utterances
    assert "rollback evidence" in utterances
    assert all("bad_interpretation" in item and "better_interpretation" in item for item in corpus)


def test_benchmark_reports_separate_scores_not_single_rollup():
    report = evaluate_pragmatic_corpus()

    assert report["activation_status"] == "bounded_pre_router_capable"
    assert report["corpus_size"] >= 16
    assert "cooperative_interpretation_accuracy" in report["scores"]
    assert "mixed_judgment_accuracy" in report["scores"]
    assert "response_shape_accuracy" in report["scores"]
    assert "overall" not in report["scores"]
    assert report["hard_invariants"]["production_route_changed"] is False


def test_adversarial_evaluation_preserves_shadow_safety():
    cases = build_adversarial_cases()
    report = evaluate_adversarial_cases()

    assert len(cases) >= 14
    assert report["passed"] is True
    assert report["safety"]["provider_calls_performed"] is False
    assert report["safety"]["production_route_changed"] is False


def test_write_pc1_artifacts_creates_json_and_reports():
    artifacts = write_pc1_artifacts()
    corpus_path = Path(artifacts["corpus_path"])

    assert corpus_path.exists()
    loaded = json.loads(corpus_path.read_text(encoding="utf-8"))
    assert len(loaded) == artifacts["summary"]["corpus_size"]
    assert (Path("reports") / "PC1_PRAGMATIC_COGNITION_FOUNDATION.json").exists()
    assert (Path("reports") / "PC1_ADVERSARIAL_PRAGMATIC_EVALUATION.json").exists()
    assert artifacts["summary"]["hard_invariants"]["provider_calls_performed"] is False
