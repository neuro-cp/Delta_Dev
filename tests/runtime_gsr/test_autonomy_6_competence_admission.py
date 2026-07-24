from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_approved_plan_execution import compile_execution_authority, run_approved_plan_execution
from orchestration.runtime.autonomy_competence_admission import (
    ACTIVATION_STATE,
    NARROW_CAPABILITY_STATEMENT,
    respond_to_competence_admission,
    review_competence_candidate,
)
from orchestration.runtime.autonomy_goal_queue_planning import approve_plan_for_future_execution, compile_plan_proposal, normalize_plan_feedback
from orchestration.runtime.autonomy_outcome_review import review_completed_outcome
from tests.runtime_gsr.test_autonomy_3_goal_queue_planning import _queued
from tests.runtime_gsr.test_autonomy_4_approved_plan_execution import _DummyProviderManager

if sys.platform == "win32":
    tcl_root = Path(sys.base_prefix) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(tcl_root / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(tcl_root / "tk8.6"))


def _approved_plan():
    goal = _queued()
    plan = compile_plan_proposal(goal)
    approval = approve_plan_for_future_execution(plan, normalize_plan_feedback("looks good"))
    return goal, plan, approval


def _a5_root(tmp_path: Path, *, mutate=None, force_revision_fail: bool = False) -> Path:
    _goal, plan, approval = _approved_plan()
    a4_root = tmp_path / "a4"
    authority = compile_execution_authority(plan, approval, issued_at="2026-07-23T00:00:00+00:00", expires_at="2026-07-25T00:00:00+00:00")
    run_approved_plan_execution(
        plan,
        approval,
        output_root=a4_root,
        authority=authority,
        force_revision_fail=force_revision_fail,
        now=lambda: datetime(2026, 7, 24, 1, 0, tzinfo=timezone.utc),
    )
    if mutate:
        mutate(a4_root)
    a5_root = tmp_path / "a5"
    review_completed_outcome(a4_root, output_root=a5_root)
    return a5_root


def _json_files(root: Path, rel: str) -> list[Path]:
    return sorted((root / rel).glob("*.json"))


def _mutate_one(root: Path, rel: str, mutate) -> None:
    path = _json_files(root, rel)[-1]
    record = json.loads(path.read_text(encoding="utf-8"))
    mutate(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")


def _a6(tmp_path: Path, *, a5_root: Path | None = None, existing=()):
    return review_competence_candidate(a5_root or _a5_root(tmp_path), output_root=tmp_path / "a6", existing_competence_roots=existing)


def test_a6_eligible_candidate_policy_and_digest_chain(tmp_path):
    result = _a6(tmp_path)
    candidate = result["candidate"]
    policy = result["policy"]
    request = result["operator_request"]

    assert policy["admission_recommendation"] == "recommend_admission"
    assert candidate["exact_behavioral_capability_statement"] == NARROW_CAPABILITY_STATEMENT
    assert candidate["admission_status"] == "pending_operator_admission_review"
    assert candidate["a5_review_digest"]
    assert candidate["a4_evaluator_digest"] == candidate["evaluator_digest"]
    assert policy["eligibility_checks"]["a5_review_digest_valid"] is True
    assert policy["eligibility_checks"]["evaluator_fixed_before_strategy_execution"] is True
    assert policy["eligibility_checks"]["hidden_and_transfer_cases_isolated"] is True
    assert policy["eligibility_checks"]["negative_controls_discriminated"] is True
    assert policy["eligibility_checks"]["no_provider_call_influenced_evaluator"] is True
    assert request["request_integrity_digest"] != request["card_digest"]
    assert request["card"]["controls"][0] == "Admit this competence"


def test_a6_explicit_admission_creates_one_inactive_unpromoted_record(tmp_path):
    result = _a6(tmp_path)
    admitted = respond_to_competence_admission(
        result["candidate"],
        result["policy"],
        result["operator_request"],
        "admit this competence",
        output_root=tmp_path / "a6",
    )
    replay = respond_to_competence_admission(
        result["candidate"],
        result["policy"],
        result["operator_request"],
        "admit this competence",
        output_root=tmp_path / "a6",
    )
    competence = admitted["accepted_competence"]

    assert admitted["status"] == "accepted_bounded_competence"
    assert replay["status"] == "already_admitted"
    assert len(_json_files(tmp_path / "a6", "accepted_competencies")) == 1
    assert competence["admission_status"] == "accepted_bounded_competence"
    assert competence["activation_state"] == ACTIVATION_STATE
    assert competence["trusted_generalization"] is False
    assert competence["promotion_state"] == "not_promoted"
    assert competence["deployment_authority"] is False
    assert competence["source_mutation_authority"] is False
    assert competence["provider_authority"] is False


def test_a6_ambiguous_response_does_not_consume_or_admit(tmp_path):
    result = _a6(tmp_path)
    response = respond_to_competence_admission(result["candidate"], result["policy"], result["operator_request"], "looks good", output_root=tmp_path / "a6")

    assert response["status"] == "clarification_required"
    assert response["consumed"] is False
    assert not _json_files(tmp_path / "a6", "accepted_competencies")
    assert not _json_files(tmp_path / "a6", "responses")


def test_a6_keep_reject_and_more_evaluation_do_not_create_competence(tmp_path):
    for phrase, status in (
        ("keep it provisional", "retained_provisional"),
        ("reject admission", "admission_rejected"),
        ("request more evaluation", "additional_evaluation_requested"),
    ):
        result = review_competence_candidate(_a5_root(tmp_path / phrase.replace(" ", "-")), output_root=tmp_path / phrase.replace(" ", "-") / "a6")
        response = respond_to_competence_admission(result["candidate"], result["policy"], result["operator_request"], phrase, output_root=tmp_path / phrase.replace(" ", "-") / "a6")
        assert response["status"] == status
        assert response["accepted_competence"] is None
        assert not _json_files(tmp_path / phrase.replace(" ", "-") / "a6", "accepted_competencies")


def test_a6_duplicate_competence_suppresses_second_record(tmp_path):
    first = _a6(tmp_path / "first")
    admitted = respond_to_competence_admission(first["candidate"], first["policy"], first["operator_request"], "admit this competence", output_root=tmp_path / "first" / "a6")
    second = review_competence_candidate(_a5_root(tmp_path / "second"), output_root=tmp_path / "second" / "a6", existing_competence_roots=(tmp_path / "first" / "a6",))

    assert admitted["accepted_competence"]
    assert second["policy"]["admission_recommendation"] == "duplicate_existing_competence"
    assert second["overlap"]["overlap_disposition"] == "duplicate_existing_competence"


def test_a6_existing_narrower_stable_identifier_competence_is_explicit_extension(tmp_path):
    existing_root = tmp_path / "existing" / "developmental_competence"
    existing_root.mkdir(parents=True)
    existing = {
        "schema": "live_general_3_developmental_reconciliation_competence_v1",
        "competence_id": "stable-id-competence",
        "learning_objective": "Learn to reconcile records by stable identifier matching.",
        "task_class": "cross_format_record_reconciliation",
    }
    (existing_root / "stable-id-competence.json").write_text(json.dumps(existing), encoding="utf-8")

    result = _a6(tmp_path, existing=(tmp_path / "existing",))

    assert result["overlap"]["overlap_disposition"] == "supersedes_narrower_competence"
    assert result["overlap"]["extends"] == "stable_identifier_reconciliation"
    assert result["policy"]["admission_recommendation"] == "recommend_admission"


def test_a6_broader_unsupported_claim_is_excluded_from_admitted_statement(tmp_path):
    a5_root = _a5_root(tmp_path)
    _mutate_one(a5_root, "capability_statements", lambda record: record.__setitem__("statement", "Can perform general entity resolution on arbitrary databases."))
    result = review_competence_candidate(a5_root, output_root=tmp_path / "a6")

    assert "general entity resolution" not in result["candidate"]["exact_behavioral_capability_statement"].lower()
    assert "arbitrary database reconciliation" in result["candidate"]["excluded_behavior"]
    assert result["policy"]["admission_recommendation"] == "recommend_admission"


def test_a6_evaluator_digest_mismatch_integrity_stop(tmp_path):
    a5_root = _a5_root(tmp_path)
    _mutate_one(a5_root, "reviews", lambda record: record.__setitem__("evaluator_digest", "changed"))
    result = review_competence_candidate(a5_root, output_root=tmp_path / "a6")

    assert result["policy"]["admission_recommendation"] == "integrity_stop"
    assert "a5_review_digest_valid" in result["policy"]["failed_checks"]


def test_a6_missing_negative_or_transfer_evidence_requests_more_evaluation(tmp_path):
    negative_root = _a5_root(tmp_path / "negative", mutate=lambda a4: _mutate_one(a4, "evaluator", lambda record: record.__setitem__("negative_controls", False)))
    negative = review_competence_candidate(negative_root, output_root=tmp_path / "negative" / "a6")
    assert negative["policy"]["admission_recommendation"] == "request_additional_evaluation"

    transfer_root = _a5_root(tmp_path / "transfer")
    _mutate_one(transfer_root, "transfer_reviews", lambda record: dict(record["family_results"])["transfer"].__setitem__("present", []))
    transfer = review_competence_candidate(transfer_root, output_root=tmp_path / "transfer" / "a6")
    assert transfer["policy"]["admission_recommendation"] == "request_additional_evaluation"


def test_a6_clause_support_mapping_and_restart_exactness(tmp_path):
    first = _a6(tmp_path)
    second = _a6(tmp_path)

    assert all(row["admission_eligibility"] for row in first["candidate"]["clause_support_table"])
    assert second["duplicate_suppressed"] is True
    assert second["candidate"]["admission_candidate_id"] == first["candidate"]["admission_candidate_id"]
    assert len(_json_files(tmp_path / "a6", "admission_candidates")) == 1
    assert len(_json_files(tmp_path / "a6", "operator_requests")) == 1
    assert len(_json_files(tmp_path / "a6", "narration")) == 4


def test_a6_stale_request_is_rejected_before_admission(tmp_path):
    result = _a6(tmp_path)
    stale_request = dict(result["operator_request"])
    stale_request["request_integrity_digest"] = "stale"

    response = respond_to_competence_admission(result["candidate"], result["policy"], stale_request, "admit this competence", output_root=tmp_path / "a6")

    assert response["status"] == "stale_or_mismatched_request"
    assert not _json_files(tmp_path / "a6", "accepted_competencies")


def test_a6_explain_scope_does_not_consume_request(tmp_path):
    result = _a6(tmp_path)
    response = respond_to_competence_admission(result["candidate"], result["policy"], result["operator_request"], "explain the scope", output_root=tmp_path / "a6")

    assert response["status"] == "scope_explained"
    assert response["consumed"] is False
    assert not _json_files(tmp_path / "a6", "responses")


def test_tk_a6_admission_card_and_keep_provisional(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ROOT", tmp_path / "live-runtime-4")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ACCEPTED_ROOT", tmp_path / "accepted")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    root = tk.Tk()
    root.update()
    app = DELTA.DeltaApp(root)
    try:
        app.operator_ux_root = tmp_path / "operator-ux"
        _goal, plan, approval = _approved_plan()
        (app.operator_ux_root / "autonomy_3_plans").mkdir(parents=True, exist_ok=True)
        (app.operator_ux_root / "autonomy_3_plan_approvals").mkdir(parents=True, exist_ok=True)
        (app.operator_ux_root / "autonomy_3_plans" / f"{plan['plan_id']}.json").write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
        (app.operator_ux_root / "autonomy_3_plan_approvals" / f"{approval['approval_id']}.json").write_text(json.dumps(approval, sort_keys=True), encoding="utf-8")
        app._refresh_operator_ux_views()
        app.a4_control_buttons["start"].invoke()
        app.a5_control_buttons["review"].invoke()
        app.a6_control_buttons["review"].invoke()
        assert app.a6_admission_status.get() == "A6: recommend admission"
        assert app.active_operator_ux_request["schema"] == "autonomy_6_operator_competence_admission_request_v1"
        app.a6_control_buttons["explain"].invoke()
        app.a6_control_buttons["ambiguous"].invoke()
        app.a6_control_buttons["keep"].invoke()
        assert not tuple((app.operator_ux_root / "autonomy_6_competence_admission" / "accepted_competencies").glob("*.json"))
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
