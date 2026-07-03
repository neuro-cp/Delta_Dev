from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_canonical_report import build_canonical_store_report_data, write_canonical_store_report
from orchestration.runtime.v14_canonical_revision import (
    create_canonical_revision_record,
    create_canonical_rollback_plan,
    validate_revision_record_not_applied,
    validate_rollback_plan_not_applied,
)
from orchestration.runtime.v14_canonical_store import (
    RUNTIME_V14F_INVARIANT_FLAGS,
    CanonicalMemoryStatus,
    CanonicalStoreDecisionOutcome,
    create_canonical_memory_draft,
    create_canonical_store_plan,
    create_inactive_canonical_memory_record,
    decide_canonical_store,
    validate_canonical_decision_review_only,
    validate_canonical_draft_inert,
    validate_canonical_record_inactive,
    validate_canonical_store_plan_inert,
)
from orchestration.runtime.v14_consolidation import (
    ConsolidationCandidateKind,
    create_consolidation_candidate,
    decide_consolidation_candidate,
)
from orchestration.runtime.v14_episode import TraceRiskFlag, create_episode_from_answer_trace
from orchestration.runtime.v14_feedback import (
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackSource,
    FeedbackTarget,
    capture_feedback_from_episode,
)
from orchestration.runtime.v14_replay import create_replay_batch, review_replay_batch
from orchestration.runtime.v14_trace import TraceAnswerMode, create_answer_trace


def _candidate_and_decision():
    trace = create_answer_trace(
        trace_id="trace-v14f",
        question="What future memory should be reviewed?",
        answer_mode=TraceAnswerMode.BEST_GUESS,
        confidence=0.7,
        risk_flags=(TraceRiskFlag.WEAK_EVIDENCE,),
        final_answer_summary="Record the evidence as a future candidate only.",
    )
    episode = create_episode_from_answer_trace(trace)
    feedback = capture_feedback_from_episode(
        episode,
        source=FeedbackSource.USER_EXPLICIT,
        polarity=FeedbackPolarity.CORRECTS,
        severity=FeedbackSeverity.MEDIUM,
        target=FeedbackTarget.EVIDENCE_USE,
        feedback_text="Keep this for replay review.",
        affected_concepts=("concept-v14f",),
    )
    batch = create_replay_batch(episodes=[episode], feedback_records=[feedback])
    review = review_replay_batch(batch, episodes=[episode], feedback_records=[feedback])
    candidate = create_consolidation_candidate(
        review,
        batch,
        candidate_kind=ConsolidationCandidateKind.FEEDBACK_PATTERN,
        summary="A future canonical memory should preserve evidence provenance.",
    )
    decision = decide_consolidation_candidate(candidate)
    return candidate, decision


def test_importing_canonical_design_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14F_INVARIANT_FLAGS.values())


def test_canonical_memory_draft_is_deterministic_and_inert():
    candidate, decision = _candidate_and_decision()

    first = create_canonical_memory_draft(candidate, decision, lane_scope=("reasoning",))
    second = create_canonical_memory_draft(candidate, decision, lane_scope=("reasoning",))

    assert first.draft_id == second.draft_id
    assert first.source_candidate_id == candidate.candidate_id
    assert first.provenance_refs
    assert first.active is False
    assert first.canonical_write_enabled is False
    assert validate_canonical_draft_inert(first)


def test_inactive_canonical_memory_record_does_not_connect_to_recall():
    candidate, decision = _candidate_and_decision()
    draft = create_canonical_memory_draft(candidate, decision)
    record = create_inactive_canonical_memory_record(draft)

    assert record.record_id.startswith("canonical-record-")
    assert record.created_from_candidate_id == candidate.candidate_id
    assert record.status == CanonicalMemoryStatus.PROPOSED
    assert record.active is False
    assert record.runtime_recall_enabled is False
    assert record.canonical_write_enabled is False
    assert validate_canonical_record_inactive(record)


def test_store_decisions_are_review_only_and_cover_all_outcomes():
    candidate, consolidation_decision = _candidate_and_decision()
    draft = create_canonical_memory_draft(candidate, consolidation_decision)

    outcomes = {
        decide_canonical_store(draft).outcome,
        decide_canonical_store(draft, defer=True).outcome,
        decide_canonical_store(draft, reject=True).outcome,
        decide_canonical_store(draft, require_human_review=True).outcome,
        decide_canonical_store(draft, invariant_block=True).outcome,
        decide_canonical_store(draft, eligible_for_future_write=True).outcome,
    }

    assert outcomes == {
        CanonicalStoreDecisionOutcome.DRAFT_ONLY,
        CanonicalStoreDecisionOutcome.DEFER,
        CanonicalStoreDecisionOutcome.REJECT,
        CanonicalStoreDecisionOutcome.REQUIRES_HUMAN_REVIEW,
        CanonicalStoreDecisionOutcome.BLOCKED_BY_INVARIANT,
        CanonicalStoreDecisionOutcome.ELIGIBLE_FOR_FUTURE_WRITE,
    }
    assert all(
        validate_canonical_decision_review_only(decide_canonical_store(draft, eligible_for_future_write=True))
        for _ in range(2)
    )


def test_canonical_store_plan_has_no_write_or_scheduler_authority():
    candidate, consolidation_decision = _candidate_and_decision()
    draft = create_canonical_memory_draft(candidate, consolidation_decision)
    record = create_inactive_canonical_memory_record(draft)
    decision = decide_canonical_store(draft, eligible_for_future_write=True)
    plan = create_canonical_store_plan(drafts=[draft], records=[record], decisions=[decision])

    assert plan.draft_ids == (draft.draft_id,)
    assert plan.record_ids == (record.record_id,)
    assert plan.decision_ids == (decision.decision_id,)
    assert validate_canonical_store_plan_inert(plan)
    assert plan.canonical_write_enabled is False
    assert plan.runtime_recall_enabled is False
    assert plan.scheduler_enabled is False


def test_revision_record_and_rollback_plan_are_not_applied():
    candidate, consolidation_decision = _candidate_and_decision()
    draft = create_canonical_memory_draft(candidate, consolidation_decision)
    record = create_inactive_canonical_memory_record(draft)
    store_decision = decide_canonical_store(draft)
    rollback = create_canonical_rollback_plan(
        record,
        rollback_reason="future rollback would require evidence review",
        required_evidence_or_approval=("human_review",),
    )
    revision = create_canonical_revision_record(
        record,
        store_decision,
        change_rationale="future revision ledger entry",
        rollback_plan_id=rollback.rollback_plan_id,
    )

    assert rollback.target_record_id == record.record_id
    assert rollback.applied is False
    assert revision.rollback_plan_id == rollback.rollback_plan_id
    assert revision.applied is False
    assert validate_rollback_plan_not_applied(rollback)
    assert validate_revision_record_not_applied(revision)


def test_report_data_preserves_all_boundaries():
    data = build_canonical_store_report_data()

    assert data["final_recommendation"] == "PROCEED_TEMPORARY_PRUNING_PROJECTION_DESIGN"
    assert data["safety_boundaries"]["canonical_write_enabled"] is False
    assert data["safety_boundaries"]["runtime_recall_enabled"] is False
    assert data["safety_boundaries"]["active_store_enabled"] is False
    assert data["inactive_systems"]["activation_attention_integration"] is False


def test_write_canonical_store_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14f_live_canonical_store_design.md"
    json_path = tmp_path / "runtime_v14f_live_canonical_store_design.json"

    write_canonical_store_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_TEMPORARY_PRUNING_PROJECTION_DESIGN"
    assert "Canonical memory is now represented as a governed target contract" in text
    assert "runtime_recall_enabled: False" in text
