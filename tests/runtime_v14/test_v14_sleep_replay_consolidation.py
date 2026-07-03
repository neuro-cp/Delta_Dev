from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_consolidation import (
    ConsolidationCandidateKind,
    ConsolidationDecisionOutcome,
    create_consolidation_candidate,
    decide_consolidation_candidate,
    validate_consolidation_candidate_non_mutating,
    validate_consolidation_decision_review_only,
)
from orchestration.runtime.v14_episode import TraceRiskFlag, create_episode_from_answer_trace
from orchestration.runtime.v14_feedback import (
    FeedbackPolarity,
    FeedbackSeverity,
    FeedbackSource,
    FeedbackTarget,
    capture_feedback_from_episode,
)
from orchestration.runtime.v14_feedback_to_pruning import (
    feedback_to_pruning_review_proposals,
    validate_pruning_proposal_non_mutating,
)
from orchestration.runtime.v14_lanes import RuntimeLane
from orchestration.runtime.v14_replay import (
    RUNTIME_V14E_INVARIANT_FLAGS,
    ReplayBatchStatus,
    ReplayReviewFinding,
    create_replay_batch,
    review_replay_batch,
    validate_replay_batch_non_mutating,
    validate_replay_review_non_mutating,
)
from orchestration.runtime.v14_replay_markers import create_replay_marker_from_episode, create_replay_marker_from_feedback
from orchestration.runtime.v14_replay_report import build_sleep_replay_report_data, write_sleep_replay_report
from orchestration.runtime.v14_sleep_cycle import (
    SleepCycleIntent,
    create_sleep_cycle_plan,
    validate_sleep_cycle_plan_inert,
)
from orchestration.runtime.v14_trace import TraceAnswerMode, create_answer_trace


def _episode(*, benchmark_only=False, risk_flags=(TraceRiskFlag.WEAK_EVIDENCE,)):
    trace = create_answer_trace(
        trace_id="trace-v14e",
        question="What should DELTA do with this feedback?",
        answer_mode=TraceAnswerMode.WEAK_GUESS,
        confidence=0.42,
        risk_flags=risk_flags,
        uncertainty_reason="limited evidence",
        final_answer_summary="Record it for later review.",
    )
    return create_episode_from_answer_trace(trace, benchmark_only=benchmark_only)


def _feedback(episode, *, polarity=FeedbackPolarity.CORRECTS, severity=FeedbackSeverity.MEDIUM):
    return capture_feedback_from_episode(
        episode,
        source=FeedbackSource.USER_EXPLICIT,
        polarity=polarity,
        severity=severity,
        target=FeedbackTarget.EVIDENCE_USE,
        feedback_text="This evidence needs replay review.",
        affected_concepts=("concept-review",),
        affected_lanes=(RuntimeLane.REASONING,),
    )


def test_importing_v14e_modules_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14E_INVARIANT_FLAGS.values())


def test_replay_batch_is_deterministic_and_non_mutating():
    episode = _episode()
    feedback = _feedback(episode)
    marker = create_replay_marker_from_feedback(feedback)
    proposals = feedback_to_pruning_review_proposals(
        _feedback(episode, polarity=FeedbackPolarity.FLAGS_NOISE)
    )

    first = create_replay_batch(
        episodes=[episode],
        feedback_records=[feedback],
        replay_markers=[marker],
        pruning_proposals=proposals,
    )
    second = create_replay_batch(
        pruning_proposals=proposals,
        replay_markers=[marker],
        feedback_records=[feedback],
        episodes=[episode],
    )

    assert first.batch_id == second.batch_id
    assert first.status == ReplayBatchStatus.REVIEW_READY
    assert first.item_count == 3 + len(proposals)
    assert validate_replay_batch_non_mutating(first)
    assert all(validate_pruning_proposal_non_mutating(proposal) for proposal in proposals)


def test_benchmark_only_batch_is_do_not_train():
    episode = _episode(benchmark_only=True)
    marker = create_replay_marker_from_episode(episode)
    batch = create_replay_batch(episodes=[episode], replay_markers=[marker])
    result = review_replay_batch(batch, episodes=[episode], replay_markers=[marker])

    assert batch.status == ReplayBatchStatus.BENCHMARK_ONLY_DO_NOT_TRAIN
    assert ReplayReviewFinding.BENCHMARK_ONLY in result.findings
    assert result.candidate_recommended is False
    assert validate_replay_review_non_mutating(result)


def test_replay_review_result_is_candidate_only_signal():
    episode = _episode()
    feedback = _feedback(episode)
    marker = create_replay_marker_from_feedback(feedback)
    batch = create_replay_batch(episodes=[episode], feedback_records=[feedback], replay_markers=[marker])
    result = review_replay_batch(batch, episodes=[episode], feedback_records=[feedback], replay_markers=[marker])

    assert ReplayReviewFinding.USEFUL_SIGNAL in result.findings
    assert ReplayReviewFinding.CONFLICTING_EVIDENCE in result.findings
    assert result.candidate_recommended
    assert result.canonical_write_enabled is False
    assert result.training_enabled is False
    assert result.pruning_enabled is False
    assert validate_replay_review_non_mutating(result)


def test_safety_review_does_not_recommend_consolidation_candidate():
    episode = _episode(risk_flags=(TraceRiskFlag.UNSAFE_ACTION,))
    feedback = _feedback(episode, polarity=FeedbackPolarity.FLAGS_SAFETY_RISK, severity=FeedbackSeverity.HIGH)
    batch = create_replay_batch(episodes=[episode], feedback_records=[feedback])
    result = review_replay_batch(batch, episodes=[episode], feedback_records=[feedback])

    assert ReplayReviewFinding.SAFETY_BLOCKED in result.findings
    assert result.human_review_needed
    assert result.candidate_recommended is False


def test_consolidation_candidate_is_not_canonical_memory():
    episode = _episode()
    feedback = _feedback(episode)
    batch = create_replay_batch(episodes=[episode], feedback_records=[feedback])
    result = review_replay_batch(batch, episodes=[episode], feedback_records=[feedback])
    candidate = create_consolidation_candidate(
        result,
        batch,
        candidate_kind=ConsolidationCandidateKind.FEEDBACK_PATTERN,
    )

    assert candidate.candidate_only is True
    assert candidate.canonical_memory is False
    assert candidate.source_episode_ids == (episode.episode_id,)
    assert validate_consolidation_candidate_non_mutating(candidate)


def test_consolidation_decisions_are_review_only():
    episode = _episode()
    feedback = _feedback(episode)
    batch = create_replay_batch(episodes=[episode], feedback_records=[feedback])
    result = review_replay_batch(batch, episodes=[episode], feedback_records=[feedback])
    candidate = create_consolidation_candidate(result, batch)

    outcomes = {
        decide_consolidation_candidate(candidate).outcome,
        decide_consolidation_candidate(candidate, defer=True).outcome,
        decide_consolidation_candidate(candidate, reject=True).outcome,
        decide_consolidation_candidate(candidate, require_human_review=True).outcome,
        decide_consolidation_candidate(candidate, invariant_block=True).outcome,
    }

    assert outcomes == {
        ConsolidationDecisionOutcome.CANDIDATE_ONLY,
        ConsolidationDecisionOutcome.DEFER,
        ConsolidationDecisionOutcome.REJECT,
        ConsolidationDecisionOutcome.REQUIRES_HUMAN_REVIEW,
        ConsolidationDecisionOutcome.BLOCKED_BY_INVARIANT,
    }
    for outcome in outcomes:
        decision = decide_consolidation_candidate(
            candidate,
            defer=outcome == ConsolidationDecisionOutcome.DEFER,
            reject=outcome == ConsolidationDecisionOutcome.REJECT,
            require_human_review=outcome == ConsolidationDecisionOutcome.REQUIRES_HUMAN_REVIEW,
            invariant_block=outcome == ConsolidationDecisionOutcome.BLOCKED_BY_INVARIANT,
        )
        assert decision.applied is False
        assert validate_consolidation_decision_review_only(decision)


def test_sleep_cycle_plan_is_inert():
    episode = _episode()
    batch = create_replay_batch(episodes=[episode])
    plan = create_sleep_cycle_plan(
        batches=[batch],
        intent=SleepCycleIntent.PREPARE_CONSOLIDATION_CANDIDATES,
        max_batches=1,
    )

    assert plan.batch_ids == (batch.batch_id,)
    assert plan.max_batches == 1
    assert validate_sleep_cycle_plan_inert(plan)
    assert plan.scheduler_enabled is False
    assert plan.active_replay_enabled is False


def test_report_data_keeps_training_and_canonical_writes_disabled():
    data = build_sleep_replay_report_data()

    assert data["final_recommendation"] == "PROCEED_LIVE_CANONICAL_STORE_DESIGN"
    assert data["safety_boundaries"]["training_enabled"] is False
    assert data["safety_boundaries"]["canonical_write_enabled"] is False
    assert data["inactive_systems"]["active_replay_loop"] is False


def test_write_sleep_replay_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14e_sleep_replay_consolidation_design.md"
    json_path = tmp_path / "runtime_v14e_sleep_replay_consolidation_design.json"

    write_sleep_replay_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_LIVE_CANONICAL_STORE_DESIGN"
    assert "Replay evaluates future consolidation eligibility" in text
    assert "The old `G:\\Delta_DevV0\\engine\\runtime.py` is not adopted directly." in text
