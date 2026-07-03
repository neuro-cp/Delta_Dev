from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_recall_bridge import (
    RUNTIME_V14K_INVARIANT_FLAGS,
    RecallBridgeEligibilityOutcome,
    RecallBridgeSafetyStatus,
    RecallBridgeSourceType,
    create_recall_bridge_candidate,
    create_recall_bridge_plan,
    create_recall_bridge_query,
    create_recall_bridge_report_entry,
    create_recall_bridge_source,
    create_recall_bridge_trace,
    decide_recall_bridge_candidate,
    review_recall_bridge_candidate,
    validate_recall_bridge_candidate_not_retrieved,
    validate_recall_bridge_decision_review_only,
    validate_recall_bridge_plan_inert,
    validate_recall_bridge_query_inert,
    validate_recall_bridge_report_entry_review_only,
    validate_recall_bridge_safety_review_non_approving,
    validate_recall_bridge_source_inert,
    validate_recall_bridge_trace_review_only,
)
from orchestration.runtime.v14_recall_bridge_report import (
    build_recall_bridge_report_data,
    write_recall_bridge_report,
)


def _source():
    return create_recall_bridge_source(
        source_type=RecallBridgeSourceType.CANONICAL_MEMORY_RECORD,
        source_reference_id="canonical-record-1",
        lane_scope=("reasoning",),
        provenance_reference_ids=("trace-1", "review-1", "decision-1"),
        confidence_state=0.72,
    )


def _query():
    return create_recall_bridge_query(
        query_text="How should maintenance failures be interpreted?",
        lane_scope=("reasoning",),
        source_constraints=("inactive_canonical_record",),
        evidence_requirements=("provenance", "lane_fit"),
        safety_requirements=("no_live_recall",),
    )


def _candidate():
    return create_recall_bridge_candidate(
        query=_query(),
        source=_source(),
        match_rationale="source lane and provenance match hypothetical recall review",
        evidence_score=0.8,
        uncertainty_score=0.2,
    )


def test_importing_recall_bridge_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14K_INVARIANT_FLAGS.values())


def test_recall_bridge_source_is_deterministic_and_inactive():
    source = _source()
    duplicate = _source()

    assert source.source_id == duplicate.source_id
    assert source.active is False
    assert source.recall_enabled is False
    assert source.canonical_mutation_enabled is False
    assert source.normalized_confidence() == 0.72
    assert validate_recall_bridge_source_inert(source)


def test_recall_bridge_query_does_not_execute_recall():
    query = _query()
    duplicate = _query()

    assert query.query_id == duplicate.query_id
    assert query.live_execution is False
    assert query.normalized_query == "how should maintenance failures be interpreted?"
    assert validate_recall_bridge_query_inert(query)


def test_recall_bridge_candidate_is_not_retrieved_or_active():
    candidate = _candidate()
    duplicate = _candidate()

    assert candidate.candidate_id == duplicate.candidate_id
    assert candidate.retrieved is False
    assert candidate.active_in_context is False
    assert candidate.normalized_readiness() > 0
    assert validate_recall_bridge_candidate_not_retrieved(candidate)


def test_safety_review_does_not_approve_live_recall():
    candidate = _candidate()
    review = review_recall_bridge_candidate(candidate)

    assert review.safety_status == RecallBridgeSafetyStatus.SAFE_FOR_FUTURE_REVIEW
    assert review.live_recall_approved is False
    assert "explicit future recall activation phase" in review.required_before_live_recall
    assert validate_recall_bridge_safety_review_non_approving(review)


def test_safety_review_classifies_insufficient_provenance_and_lane_mismatch():
    query = _query()
    weak_source = create_recall_bridge_source(
        source_type=RecallBridgeSourceType.CANONICAL_MEMORY_DRAFT,
        source_reference_id="draft-1",
        lane_scope=("planning",),
        provenance_reference_ids=(),
    )
    weak_candidate = create_recall_bridge_candidate(query=query, source=weak_source, evidence_score=0.8, uncertainty_score=0.2)
    review = review_recall_bridge_candidate(weak_candidate)

    assert review.safety_status == RecallBridgeSafetyStatus.INSUFFICIENT_PROVENANCE

    lane_candidate = create_recall_bridge_candidate(
        query=query,
        source=create_recall_bridge_source(
            source_type=RecallBridgeSourceType.REPLAY_REVIEW_RESULT,
            source_reference_id="replay-1",
            lane_scope=("planning",),
            provenance_reference_ids=("trace-1", "review-1"),
        ),
        evidence_score=0.8,
        uncertainty_score=0.2,
    )
    assert review_recall_bridge_candidate(lane_candidate).safety_status == RecallBridgeSafetyStatus.LANE_SCOPE_MISMATCH


def test_eligibility_decision_is_not_applied_and_does_not_activate_recall():
    candidate = _candidate()
    review = review_recall_bridge_candidate(candidate)
    decision = decide_recall_bridge_candidate(candidate, review)

    assert decision.outcome == RecallBridgeEligibilityOutcome.ELIGIBLE_FOR_FUTURE_RECALL_REVIEW
    assert decision.applied is False
    assert decision.recall_activated is False
    assert "eligibility is not activation" in decision.rationale
    assert validate_recall_bridge_decision_review_only(decision)


def test_eligibility_decision_can_require_replay_or_hypothesis_arbitration():
    candidate = _candidate()
    review = review_recall_bridge_candidate(candidate)

    replay_decision = decide_recall_bridge_candidate(candidate, review, require_replay_review=True)
    assert replay_decision.outcome == RecallBridgeEligibilityOutcome.REQUIRES_REPLAY_REVIEW

    arbitration_decision = decide_recall_bridge_candidate(candidate, review, require_hypothesis_arbitration=True)
    assert arbitration_decision.outcome == RecallBridgeEligibilityOutcome.REQUIRES_HYPOTHESIS_ARBITRATION


def test_trace_is_review_only_and_does_not_mutate_runtime_state():
    query = _query()
    source = _source()
    candidate = create_recall_bridge_candidate(query=query, source=source, evidence_score=0.8, uncertainty_score=0.2)
    review = review_recall_bridge_candidate(candidate)
    decision = decide_recall_bridge_candidate(candidate, review)
    trace = create_recall_bridge_trace(
        query=query,
        candidates=(candidate,),
        decisions=(decision,),
        safety_reviews=(review,),
        sources=(source,),
    )

    assert trace.generated_for_review_only is True
    assert trace.applied is False
    assert trace.source_reference_ids == (source.source_reference_id,)
    assert validate_recall_bridge_trace_review_only(trace)


def test_recall_bridge_plan_all_capabilities_disabled():
    query = _query()
    source = _source()
    candidate = _candidate()
    review = review_recall_bridge_candidate(candidate)
    decision = decide_recall_bridge_candidate(candidate, review)
    trace = create_recall_bridge_trace(query=query, candidates=(candidate,), decisions=(decision,), safety_reviews=(review,), sources=(source,))
    plan = create_recall_bridge_plan(
        sources=(source,),
        queries=(query,),
        candidates=(candidate,),
        decisions=(decision,),
        traces=(trace,),
    )

    assert plan.recall_bridge_enabled is False
    assert plan.live_recall_enabled is False
    assert plan.activation_integration_enabled is False
    assert plan.attention_integration_enabled is False
    assert plan.evidence_selection_integration_enabled is False
    assert plan.canonical_write_enabled is False
    assert plan.memory_mutation_enabled is False
    assert plan.runtime_recall_mutation_enabled is False
    assert plan.training_enabled is False
    assert plan.provider_calls_enabled is False
    assert plan.specialist_routing_enabled is False
    assert plan.scheduler_enabled is False
    assert validate_recall_bridge_plan_inert(plan)


def test_report_entry_is_review_only():
    query = _query()
    source = _source()
    candidate = _candidate()
    review = review_recall_bridge_candidate(candidate)
    decision = decide_recall_bridge_candidate(candidate, review)
    trace = create_recall_bridge_trace(query=query, candidates=(candidate,), decisions=(decision,), safety_reviews=(review,), sources=(source,))
    entry = create_recall_bridge_report_entry(
        trace=trace,
        candidates=(candidate,),
        decisions=(decision,),
        safety_reviews=(review,),
        unresolved_gaps=("live recall activation phase missing",),
    )

    assert entry.generated_for_review_only is True
    assert "none retrieved into runtime context" in entry.candidate_summary
    assert entry.unresolved_gaps == ("live recall activation phase missing",)
    assert validate_recall_bridge_report_entry_review_only(entry)


def test_recall_bridge_report_data_states_design_only_non_mutating_status():
    data = build_recall_bridge_report_data()

    assert data["final_recommendation"] == "PROCEED_STRUCTURAL_SEMANTIC_ADAPTER_DESIGN"
    assert data["safety_boundaries"]["recall_bridge_enabled"] is False
    assert data["safety_boundaries"]["live_recall_enabled"] is False
    assert data["safety_boundaries"]["activation_integration_enabled"] is False
    assert data["safety_boundaries"]["attention_integration_enabled"] is False
    assert data["safety_boundaries"]["canonical_write_enabled"] is False
    assert data["inactive_systems"]["canonical_memory_as_live_source"] is False


def test_write_recall_bridge_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14k_recall_bridge_design.md"
    json_path = tmp_path / "runtime_v14k_recall_bridge_design.json"

    write_recall_bridge_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_STRUCTURAL_SEMANTIC_ADAPTER_DESIGN"
    assert "bridge design != live recall" in text
    assert "A recall bridge candidate is not retrieved memory" in text
