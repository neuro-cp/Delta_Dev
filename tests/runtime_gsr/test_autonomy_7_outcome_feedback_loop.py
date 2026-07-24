from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from orchestration.runtime.autonomy_approved_plan_execution import compile_execution_authority, run_approved_plan_execution
from orchestration.runtime.autonomy_competence_admission import respond_to_competence_admission, review_competence_candidate
from orchestration.runtime.autonomy_goal_queue_planning import approve_plan_for_future_execution, compile_plan_proposal, normalize_plan_feedback
from orchestration.runtime.autonomy_outcome_feedback_loop import run_outcome_feedback_loop
from orchestration.runtime.autonomy_outcome_review import review_completed_outcome
from tests.runtime_gsr.test_autonomy_3_goal_queue_planning import _queued


def _a4_a5_a6(tmp_path: Path, *, admit: bool) -> tuple[Path, Path, Path]:
    goal = _queued()
    plan = compile_plan_proposal(goal)
    approval = approve_plan_for_future_execution(plan, normalize_plan_feedback("looks good"))
    a4 = tmp_path / "a4"
    authority = compile_execution_authority(plan, approval, issued_at="2026-07-23T00:00:00+00:00", expires_at="2026-07-25T00:00:00+00:00")
    run_approved_plan_execution(plan, approval, output_root=a4, authority=authority, now=lambda: datetime(2026, 7, 24, 1, 0, tzinfo=timezone.utc))
    a5 = tmp_path / "a5"
    review_completed_outcome(a4, output_root=a5)
    a6 = tmp_path / "a6"
    result = review_competence_candidate(a5, output_root=a6)
    phrase = "admit this competence" if admit else "keep it provisional"
    respond_to_competence_admission(result["candidate"], result["policy"], result["operator_request"], phrase, output_root=a6)
    return a4, a5, a6


def test_a7_admitted_competence_suppresses_exact_goal_and_retains_limitations(tmp_path):
    a4, a5, a6 = _a4_a5_a6(tmp_path, admit=True)
    result = run_outcome_feedback_loop(a4_root=a4, a5_root=a5, a6_root=a6, output_root=tmp_path / "a7")

    assert result["status"] == "AUTONOMY_7_OUTCOME_FEEDBACK_LOOP_PASSED"
    feedback = result["feedback"]
    assert feedback["goal_transition"] == "resolved"
    assert feedback["capability_state_transition"]["condition_state"] == "accepted_bounded_inactive"
    assert "missing_or_unreliable_identifier_reconciliation" in feedback["stale_candidates_suppressed"]
    assert "transfer_beyond_retained_fixture_families" in feedback["active_candidates_retained"]
    assert result["ranking"]["recommended_candidate"]["condition_key"] in set(feedback["active_candidates_retained"])
    assert feedback["execution_started"] is False


def test_a7_provisional_evidence_does_not_suppress_full_goal(tmp_path):
    a4, a5, a6 = _a4_a5_a6(tmp_path, admit=False)
    result = run_outcome_feedback_loop(a4_root=a4, a5_root=a5, a6_root=a6, output_root=tmp_path / "a7")

    feedback = result["feedback"]
    assert feedback["goal_transition"] == "retained_provisional"
    assert feedback["resolved_condition_keys"] == ()
    assert "competence_not_admitted" in feedback["unresolved_condition_keys"]
    assert feedback["stale_candidates_suppressed"] == ()


def test_a7_restart_exactness_and_no_duplicate_feedback(tmp_path):
    a4, a5, a6 = _a4_a5_a6(tmp_path, admit=True)
    first = run_outcome_feedback_loop(a4_root=a4, a5_root=a5, a6_root=a6, output_root=tmp_path / "a7")
    second = run_outcome_feedback_loop(a4_root=a4, a5_root=a5, a6_root=a6, output_root=tmp_path / "a7")

    assert second["duplicate_suppressed"] is True
    assert second["feedback"]["feedback_id"] == first["feedback"]["feedback_id"]
    assert len(tuple((tmp_path / "a7" / "feedback_records").glob("*.json"))) == 1


def test_a7_missing_evidence_integrity_stop_does_not_manufacture_goal(tmp_path):
    result = run_outcome_feedback_loop(a4_root=tmp_path / "missing-a4", a5_root=tmp_path / "missing-a5", a6_root=tmp_path / "missing-a6", output_root=tmp_path / "a7")

    assert result["status"] == "AUTONOMY_7_OUTCOME_FEEDBACK_LOOP_INTEGRITY_STOP"
    assert result["feedback"]["first_missing_transition"] == "missing_a4_or_a5_review"
    assert not (tmp_path / "a7" / "rankings").exists()


def test_a7_stale_evidence_cannot_outrank_newer_resolved_evidence(tmp_path):
    a4, a5, a6 = _a4_a5_a6(tmp_path, admit=True)
    result = run_outcome_feedback_loop(a4_root=a4, a5_root=a5, a6_root=a6, output_root=tmp_path / "a7")

    suppressed = {item["condition_key"]: item["suppression_reason"] for item in result["ranking"]["suppressed_candidates"]}
    assert suppressed["missing_or_unreliable_identifier_reconciliation"] == "already_resolved_by_accepted_competence"
