from __future__ import annotations

import json
import os
import sys
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path

import DELTA
from orchestration.runtime.autonomy_approved_plan_execution import compile_execution_authority, run_approved_plan_execution
from orchestration.runtime.autonomy_goal_queue_planning import approve_plan_for_future_execution, compile_plan_proposal, normalize_plan_feedback
from orchestration.runtime.autonomy_outcome_review import (
    explain_review_evidence,
    respond_to_outcome_review,
    review_completed_outcome,
    verify_artifact_integrity,
)
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


def _a4_root(tmp_path: Path, *, force_revision_fail: bool = False, initial_pass: bool = False) -> tuple[Path, dict[str, object]]:
    _goal, plan, approval = _approved_plan()
    root = tmp_path / "a4"
    authority = compile_execution_authority(plan, approval, issued_at="2026-07-23T00:00:00+00:00", expires_at="2026-07-25T00:00:00+00:00")
    result = run_approved_plan_execution(
        plan,
        approval,
        output_root=root,
        force_revision_fail=force_revision_fail,
        initial_pass=initial_pass,
        authority=authority,
        now=lambda: datetime(2026, 7, 24, 1, 0, tzinfo=timezone.utc),
    )
    return root, result


def _json_files(root: Path, rel: str) -> list[Path]:
    return sorted((root / rel).glob("*.json"))


def _mutate_one(root: Path, rel: str, mutate) -> dict[str, object]:
    path = _json_files(root, rel)[-1]
    record = json.loads(path.read_text(encoding="utf-8"))
    mutate(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def test_a5_reviews_a4_artifacts_independently_and_does_not_admit_competence(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")
    review = result["review"]

    assert result["status"] == "AUTONOMY_5_OUTCOME_REVIEW_PASSED"
    assert review["provisional_disposition"] == "candidate_for_competence_admission_review"
    assert review["integrity_passed"] is True
    assert review["accepted_competence_created"] is False
    assert review["capability_promotion"] is False
    assert review["execution_performed_by_a5"] is False
    assert review["provider_calls"] == 0
    assert result["operator_request"]["accept_competence_action_present"] is False


def test_a5_digest_chain_evaluator_immutability_hidden_isolation_and_lifecycle(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    bundle_result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")
    integrity = bundle_result["integrity"]
    revision = bundle_result["revision_effectiveness"]

    assert integrity["passed"] is True
    assert integrity["plan_digest_matches_approval"] is True
    assert integrity["approval_matches_authority"] is True
    assert integrity["evaluator_fixed_before_strategy"] is True
    assert integrity["hidden_case_isolation_confirmed"] is True
    assert integrity["no_duplicate_semantic_execution"] is True
    assert revision["evaluator_digest_before"] == revision["evaluator_digest_after"]


def test_a5_revision_effectiveness_transfer_and_negative_controls_are_separate(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")
    revision = result["revision_effectiveness"]
    transfer = result["transfer_review"]

    assert "ambiguous_near_match" in revision["cases_improved"]
    assert "adversarial_similarity" in revision["cases_improved"]
    assert not revision["regressions"]
    assert transfer["family_results"]["visible"]["all_passed"] is True
    assert transfer["family_results"]["transfer"]["all_passed"] is True
    assert transfer["family_results"]["adversarial"]["all_passed"] is True
    assert transfer["negative_controls_discriminative"] is True


def test_a5_failed_after_revision_disposition(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path, force_revision_fail=True)
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")

    assert result["review"]["provisional_disposition"] == "failed_after_revision"
    assert result["review"]["accepted_competence_created"] is False


def test_a5_initial_pass_with_transfer_is_provisional_supported_not_admitted(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path, initial_pass=True)
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")

    assert result["review"]["provisional_disposition"] == "provisional_transfer_supported"
    assert result["review"]["accepted_competence_created"] is False


def test_a5_missing_evaluator_provenance_is_insufficient_evidence(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    _mutate_one(a4_root, "evaluator", lambda record: record.pop("evaluator_provenance", None))
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")

    assert result["review"]["provisional_disposition"] == "insufficient_evidence"


def test_a5_evaluator_mutation_and_hidden_leakage_integrity_stop(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path / "mutated")
    _mutate_one(a4_root, "strategies", lambda record: record.__setitem__("evaluator_digest", "changed"))
    mutated = review_completed_outcome(a4_root, output_root=tmp_path / "a5-mutated")
    assert mutated["status"] == "AUTONOMY_5_OUTCOME_REVIEW_INTEGRITY_STOP"
    assert "strategy_evaluator_digest_mismatch" in mutated["review"]["integrity_reasons"]

    leak_root, _a4 = _a4_root(tmp_path / "leak")
    _mutate_one(leak_root, "strategies", lambda record: record.__setitem__("hidden_expected_outputs_seen", True))
    leaked = review_completed_outcome(leak_root, output_root=tmp_path / "a5-leak")
    assert leaked["status"] == "AUTONOMY_5_OUTCOME_REVIEW_INTEGRITY_STOP"
    assert "hidden_case_leakage" in leaked["review"]["integrity_reasons"]


def test_a5_negative_controls_not_discriminative_requires_more_evaluation(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    _mutate_one(a4_root, "evaluator", lambda record: record.__setitem__("negative_controls", False))
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")

    assert result["review"]["provisional_disposition"] == "additional_evaluation_required"
    assert result["transfer_review"]["negative_controls_discriminative"] is False


def test_a5_unsupported_overclaim_removed_from_competence_statement(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    _mutate_one(a4_root, "final_synthesis", lambda record: record.__setitem__("capability_claim", "can reconcile arbitrary data"))
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")

    assert result["claims_audit"]["unsupported_claims_removed"] == ("can reconcile arbitrary data",)
    assert "arbitrary" not in result["capability_statement"]["statement"].lower()


def test_a5_duplicate_review_suppressed_and_restart_exact(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    first = review_completed_outcome(a4_root, output_root=tmp_path / "a5")
    second = review_completed_outcome(a4_root, output_root=tmp_path / "a5")

    assert second["duplicate_suppressed"] is True
    assert second["review"]["review_id"] == first["review"]["review_id"]
    assert len(_json_files(tmp_path / "a5", "reviews")) == 1
    assert len(_json_files(tmp_path / "a5", "operator_requests")) == 1


def test_a5_explanation_does_not_consume_and_response_consumed_once(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")
    explanation = explain_review_evidence(result["review"])
    response = respond_to_outcome_review(result["review"], result["operator_request"], "keep it provisional", output_root=tmp_path / "a5")
    duplicate = respond_to_outcome_review(result["review"], result["operator_request"], "keep it provisional", output_root=tmp_path / "a5")

    assert "No competence is admitted" in explanation
    assert response["response"]["consumed"] is True
    assert duplicate["response"]["response_id"] == response["response"]["response_id"]
    assert len(_json_files(tmp_path / "a5", "responses")) == 1
    assert response["queued_a6_candidate"] is None


def test_a5_send_to_competence_review_queues_candidate_only(tmp_path):
    a4_root, _a4 = _a4_root(tmp_path)
    result = review_completed_outcome(a4_root, output_root=tmp_path / "a5")
    response = respond_to_outcome_review(result["review"], result["operator_request"], "send it for competence review", output_root=tmp_path / "a5")

    queued = response["queued_a6_candidate"]
    assert queued["schema"] == "autonomy_6_review_candidate_queued_v1"
    assert queued["competence_admitted"] is False
    assert queued["autonomy_6_started"] is False
    assert response["response"]["capability_promotion"] is False


def test_a5_module_does_not_import_a4_execution_controller():
    source = Path("orchestration/runtime/autonomy_outcome_review.py").read_text(encoding="utf-8")

    assert "run_approved_plan_execution" not in source
    assert "resume_paused_execution" not in source
    assert "recover_prepared_execution" not in source


def test_tk_a5_review_card_and_response_do_not_admit_competence(monkeypatch, tmp_path):
    monkeypatch.setattr(DELTA, "ProviderManager", _DummyProviderManager)
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_1B_ROOT", tmp_path / "live-runtime-1b")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_2_ROOT", tmp_path / "live-runtime-2")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_3_ROOT", tmp_path / "live-runtime-3")
    monkeypatch.setattr(DELTA, "LIVE_RUNTIME_4_ROOT", tmp_path / "live-runtime-4")
    monkeypatch.setattr(DELTA, "OAR_LIVE_DEVELOPMENT_STATE_PATH", tmp_path / "oar-ui-state.json")
    root = tk.Tk()
    root.update()
    app = DELTA.DeltaApp(root)
    try:
        app.operator_ux_root = tmp_path / "operator-ux"
        _goal, plan, approval = _approved_plan()
        plan_dir = app.operator_ux_root / "autonomy_3_plans"
        approval_dir = app.operator_ux_root / "autonomy_3_plan_approvals"
        plan_dir.mkdir(parents=True, exist_ok=True)
        approval_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / f"{plan['plan_id']}.json").write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
        (approval_dir / f"{approval['approval_id']}.json").write_text(json.dumps(approval, sort_keys=True), encoding="utf-8")
        app._refresh_operator_ux_views()

        app.a4_control_buttons["start"].invoke()
        app._refresh_operator_ux_views()
        app.a5_control_buttons["review"].invoke()
        assert app.a5_review_status.get() == "A5: candidate for competence admission review"
        assert app.active_operator_ux_request["schema"] == "autonomy_5_operator_outcome_review_request_v1"
        app.a5_control_buttons["explain"].invoke()
        app.a5_control_buttons["send"].invoke()

        queued = tuple((app.operator_ux_root / "autonomy_5_outcome_review" / "queued_a6_candidates").glob("*.json"))
        accepted = tuple((app.operator_ux_root / "accepted_competencies").glob("*.json"))
        assert len(queued) == 1
        assert not accepted
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass
