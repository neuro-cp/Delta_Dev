from __future__ import annotations

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_output_discipline import (
    ACTION_CAUTION_PHRASE,
    BEST_GUESS_PREFIX,
    LOW_CONFIDENCE_PHRASE,
    SAFE_UNKNOWN_LOOKUP_PHRASE,
    AnswerConfidenceBand,
    UnknownAnswerReason,
    block_overconfident_phrasing,
    decide_output_mode,
    format_best_guess_answer,
    format_unknown_lookup_notice,
    format_uncertain_answer,
)
from orchestration.runtime.v14_specialist_router import (
    SpecialistDomain,
    SpecialistResponseDraft,
    classify_question_domain,
    merge_specialist_response,
    select_specialist_route,
    should_route_to_specialist,
)


def test_insufficient_evidence_does_not_direct_answer():
    decision = decide_output_mode(evidence_count=0, confidence=0.2)

    assert decision.confidence_band == AnswerConfidenceBand.INSUFFICIENT_EVIDENCE
    assert decision.reason == UnknownAnswerReason.MISSING_EVIDENCE
    assert not decision.should_answer
    assert decision.should_abstain


def test_unknown_lookup_notice_formatting_works():
    assert format_unknown_lookup_notice() == SAFE_UNKNOWN_LOOKUP_PHRASE


def test_best_guess_formatting_works():
    assert format_best_guess_answer("the route is probably unsafe").startswith(BEST_GUESS_PREFIX)


def test_high_noise_risk_blocks_overconfident_phrasing():
    decision = decide_output_mode(evidence_count=3, confidence=0.7, noise_risk=0.9)
    text = block_overconfident_phrasing("This definitely must always work.", decision)

    assert decision.reason == UnknownAnswerReason.HIGH_NOISE_RISK
    assert decision.confidence_band == AnswerConfidenceBand.WEAK_GUESS
    assert "definitely" not in text.lower()
    assert "must" not in text.lower()
    assert "always" not in text.lower()


def test_unsafe_action_risk_abstains_or_bounds_answer():
    decision = decide_output_mode(evidence_count=3, confidence=0.8, unsafe_action_risk=True)

    assert decision.confidence_band == AnswerConfidenceBand.ABSTAIN
    assert decision.should_abstain
    assert format_uncertain_answer(decision, "take the action") == ACTION_CAUTION_PHRASE


def test_low_confidence_abstention_phrase_is_available():
    decision = decide_output_mode(evidence_count=0, confidence=0.1)

    assert format_uncertain_answer(decision, "answer") == LOW_CONFIDENCE_PHRASE


def test_route_to_specialist_formats_notice_without_provider_call():
    decision = decide_output_mode(evidence_count=1, confidence=0.3, needs_specialist=True)

    assert decision.should_route
    assert format_uncertain_answer(decision, "answer") == SAFE_UNKNOWN_LOOKUP_PHRASE


def test_specialist_router_classifies_simple_examples():
    examples = {
        "Fix this Python function": SpecialistDomain.CODE,
        "Calculate the derivative": SpecialistDomain.MATH,
        "Is this contract legal": SpecialistDomain.LAW,
        "What symptom needs medical treatment": SpecialistDomain.MEDICAL,
        "How should I rebalance this investment": SpecialistDomain.FINANCE,
        "Design a scientific experiment": SpecialistDomain.SCIENCE,
        "Build a project plan and schedule": SpecialistDomain.PLANNING,
        "Recall the previous memory": SpecialistDomain.MEMORY,
        "Tell me something ordinary": SpecialistDomain.GENERAL,
    }

    for question, domain in examples.items():
        assert classify_question_domain(question) == domain


def test_specialist_route_defaults_allowed_to_call_now_false():
    route = select_specialist_route("Fix this Python function")

    assert route.domain == SpecialistDomain.CODE
    assert route.requires_external_call
    assert route.allowed_to_call_now is False
    assert should_route_to_specialist(route)


def test_merge_specialist_response_does_not_overstate_confidence():
    route = select_specialist_route("Is this contract legal", confidence=0.9)
    response = SpecialistResponseDraft(
        domain=SpecialistDomain.LAW,
        answer="the clause may need review",
        confidence=0.3,
        caveats=("not legal advice",),
    )

    merged = merge_specialist_response(route=route, response=response, base_answer="low evidence")

    assert merged.startswith("A low-confidence specialist draft suggests")
    assert "not legal advice" in merged


def test_importing_output_scaffolds_does_not_change_model_b_or_hyb1_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
