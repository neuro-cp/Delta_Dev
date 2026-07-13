from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


MISSION = "Improve demonstrated language comprehension and scholarly discussion ability."


def _compiled_mission() -> tuple[gsr.MissionCompilationResult, gsr.MissionApprovalDisposition]:
    request = gsr.make_mission_compilation_request(
        MISSION,
        baseline_evaluation_id="baseline-language-1",
        requested_sequence=10,
    )
    authorization = gsr.make_mission_compilation_authorization(request, issued_sequence=11)
    result = gsr.compile_language_development_mission(request, authorization, sequence=12)
    assert result.accepted
    assert result.compiled_objective is not None
    approval = gsr.approve_compiled_mission(result.compiled_objective, operator_identity="operator", sequence=13)
    return result, approval


def _review_item() -> gsr.OperatorReviewItem:
    compiled, _approval = _compiled_mission()
    assert compiled.compiled_objective is not None
    return gsr.make_evaluation_review_item(
        parent_mission_id="mission-language-1",
        compiled_objective_id=compiled.compiled_objective.compiled_objective_id,
        capability_gap_id="gap-thesis-assumption-evidence",
        proposal_id="proposal-language-1",
        parent_mission=MISSION,
        current_blocker="weak evidence versus assertion distinction",
        capability_specification={"capability_id": "claim_evidence_distinction", "purpose": "distinguish assertion from support"},
        architecture_alternatives=(
            {"option_id": "reuse-renderer", "summary": "extend existing response analysis templates"},
            {"option_id": "new-module", "summary": "add isolated analysis helper"},
        ),
        selected_design={"option_id": "reuse-renderer", "reason": "minimum viable reuse"},
        exact_affected_files=("fixtures/language_analyzer.py",),
        full_patch_or_structured_change="replace exact fixture helper text",
        focused_tests=("pytest tests/fixtures/test_language_analyzer.py -q",),
        adjacent_regressions=("pytest tests/runtime_gsr/test_gsr_e_objective_cycle.py -q",),
        sandbox_results={"classification": "passed", "cleanup": "verified"},
        score_change={"evidence_assertion_distinction": 0.18},
        artifact_chain_digest="chain-language-1",
        source_precondition_hashes={"fixtures/language_analyzer.py": "pre-hash"},
        resources_used=({"identity": "baseline-language-1", "authority": "operator-approved fixture"},),
        model_provider_identity="none",
    )


def _accept_disposition(item: gsr.OperatorReviewItem) -> gsr.OperatorProposalDispositionResult:
    request = gsr.make_operator_proposal_disposition_request(
        item,
        requested_disposition="accepted",
        reason_code="operator_comment",
        operator_comment="low-risk fixture proposal accepted",
        ui_action_id="ui-accept-1",
        sequence=20,
    )
    authorization = gsr.make_operator_proposal_disposition_authorization(
        request,
        operator_identity="operator",
        issued_sequence=21,
    )
    return gsr.apply_operator_proposal_disposition(item, request, authorization, sequence=22)


def test_oar_1a_mission_compilation_requires_operator_approval_and_preserves_mission():
    result, approval = _compiled_mission()
    compiled = result.compiled_objective

    assert compiled is not None
    assert compiled.original_operator_mission == MISSION
    assert "thesis_identification" in compiled.measurable_dimensions
    assert compiled.resource_budgets["maximum_capability_campaigns"] == 3
    assert "mission_approval" in compiled.operator_decisions_required
    assert result.mission_started is False
    assert result.source_application_authorized is False
    assert result.capability_activated is False
    assert result.consumed_authorization is not None
    assert result.consumed_authorization.consumed is True
    assert approval.starts_exactly_one_mission is True

    bad_request = replace(result.request, network_requested=True)
    bad = gsr.compile_language_development_mission(bad_request, result.original_authorization, sequence=12)
    assert bad.accepted is False
    assert bad.reason == "mission_compilation_scope_denied"


def test_oar_1b_review_queue_bridges_complete_items_without_application_authority():
    item = _review_item()
    queue = gsr.EvaluationReviewQueue(queue_id="queue-1")
    updated = gsr.enqueue_evaluation_review_item(queue, item)

    assert len(updated.review_items) == 1
    queued = updated.review_items[0]
    assert queued["parent_mission"] == MISSION
    assert queued["current_blocker"] == "weak evidence versus assertion distinction"
    assert queued["exact_affected_files"] == ("fixtures/language_analyzer.py",)
    assert queued["full_patch_or_structured_change"]
    assert queued["artifact_chain_digest"] == "chain-language-1"
    assert queued["application_authorized"] is False
    assert queued["application_performed"] is False
    assert updated.direct_ui_write_performed is False


def test_oar_1c_accept_decline_and_needs_modification_are_immutable_one_shot_dispositions():
    item = _review_item()
    accepted = _accept_disposition(item)
    assert accepted.accepted
    assert accepted.disposition is not None
    assert accepted.disposition.operator_disposition == "accepted"
    assert accepted.consumed_authorization is not None
    assert accepted.consumed_authorization.consumed is True
    assert accepted.application_performed is False
    assert accepted.source_written is False

    duplicate = gsr.apply_operator_proposal_disposition(
        item,
        accepted.request,
        accepted.original_authorization,
        (accepted.disposition,),
        sequence=23,
    )
    assert duplicate.accepted is False
    assert duplicate.reason == "duplicate_terminal_disposition"

    decline_request = gsr.make_operator_proposal_disposition_request(
        item,
        requested_disposition="declined",
        reason_code="insufficient_evidence",
        operator_comment="declined",
        ui_action_id="ui-decline-1",
        sequence=24,
    )
    decline_auth = gsr.make_operator_proposal_disposition_authorization(decline_request, operator_identity="operator", issued_sequence=25)
    decline = gsr.apply_operator_proposal_disposition(item, decline_request, decline_auth, sequence=26)
    assert decline.accepted
    assert decline.disposition.operator_disposition == "declined"

    revision_request = gsr.make_operator_proposal_disposition_request(
        item,
        requested_disposition="needs_modification",
        reason_code="needs_narrower_scope",
        operator_comment="revise",
        ui_action_id="ui-revise-1",
        sequence=27,
    )
    revision_auth = gsr.make_operator_proposal_disposition_authorization(revision_request, operator_identity="operator", issued_sequence=28)
    revision = gsr.apply_operator_proposal_disposition(item, revision_request, revision_auth, sequence=29)
    assert revision.accepted
    assert revision.disposition.creates_revision_request is True
    assert revision.disposition.revision_request_id


def test_oar_1d_1e_exact_application_and_validation_use_existing_governed_path(tmp_path: Path):
    item = _review_item()
    accepted = _accept_disposition(item)
    target = tmp_path / "fixtures" / "language_analyzer.py"
    target.parent.mkdir()
    target.write_text("OLD\n", encoding="utf-8")
    before_hash = gsr.inspect_application_targets_read_only(tmp_path, ("fixtures/language_analyzer.py",)).current_target_hashes["fixtures/language_analyzer.py"]
    item = replace(item, source_precondition_hashes={"fixtures/language_analyzer.py": before_hash})

    evaluation = gsr.SandboxEvidenceEvaluation(
        evaluation_id="eval-oar",
        cycle_id="cycle-oar",
        plan_id="plan-oar",
        attempt_id="attempt-oar",
        request_id="request-oar",
        authorization_id="auth-oar",
        evidence_digest="digest-oar",
        accepted_for_operator_review=True,
        classification="execution_succeeded",
        reason="passed",
        findings=(),
        execution_started=True,
        execution_succeeded=True,
        command_failed=False,
        budget_compliant=True,
        output_within_policy=True,
        artifacts_within_policy=True,
        writes_within_policy=True,
        cleanup_verified=True,
        live_source_unchanged=True,
        evidence_complete=True,
        evidence_consistent=True,
    )
    disposition_record = gsr.SandboxEvaluationDispositionRecord(
        record_id="record-oar",
        evaluation_id=evaluation.evaluation_id,
        disposition_request_id="disp-request-oar",
        disposition_id=accepted.disposition.disposition_id,
        cycle_id=evaluation.cycle_id,
        plan_id=evaluation.plan_id,
        attempt_id=evaluation.attempt_id,
        request_id=evaluation.request_id,
        authorization_id=evaluation.authorization_id,
        evidence_digest=evaluation.evidence_digest,
        operator_disposition="accept_evidence_for_future_application_consideration",
        operator_issued=True,
        issued_sequence=30,
        accepted_evidence=True,
    )
    artifact = gsr.build_application_artifact_from_review_item(item, evaluation, disposition_record)
    request = gsr.make_application_request(evaluation, disposition_record, artifact, requested_sequence=31)
    authorization = gsr.make_application_authorization(request, issued_sequence=32, expiration_sequence=40)
    eligibility = gsr.evaluate_application_eligibility(evaluation, disposition_record, artifact, request, authorization, sequence=33)
    expected_post = {"fixtures/language_analyzer.py": hashlib.sha256("NEW\n".encode("utf-8")).hexdigest()}
    operation = gsr.ApplicationPlanOperation(
        sequence=1,
        operation="apply_exact_reviewed_text_change",
        target_path="fixtures/language_analyzer.py",
        expected_current_hash=before_hash,
        expected_post_application_hash=expected_post["fixtures/language_analyzer.py"],
        rollback_operation="restore_exact_content",
        rollback_artifact_id="rollback-oar",
        rollback_target_path="fixtures/language_analyzer.py",
        rollback_expected_hash=before_hash,
    )
    plan = gsr.make_application_plan(
        eligibility,
        ordered_target_operations=(operation,),
        expected_post_application_hashes=expected_post,
        rollback_metadata=(
            {
                "target_path": "fixtures/language_analyzer.py",
                "rollback_operation": "restore_exact_content",
                "rollback_target_path": "fixtures/language_analyzer.py",
                "rollback_artifact_id": "rollback-oar",
                "rollback_expected_hash": before_hash,
            },
        ),
        required_validation_commands=("fixture-focused",),
        application_sequence=34,
    )
    preflight = gsr.evaluate_application_preflight(eligibility, plan, root=tmp_path, sequence=35)
    result = gsr.execute_governed_application_attempt(
        preflight,
        plan,
        root=tmp_path,
        reviewed_text_by_target={"fixtures/language_analyzer.py": "NEW\n"},
        validation_results={"fixture-focused": True},
        sequence=36,
    )
    validation = gsr.classify_post_application_validation(
        result,
        focused_tests_passed=True,
        adjacent_regressions_passed=True,
        startup_smoke_passed=True,
    )

    assert result.accepted
    assert result.application_performed is True
    assert result.consumed_authorization.consumed is True
    assert target.read_text(encoding="utf-8") == "NEW\n"
    assert validation.classification == "application_validated"
    assert validation.rollback_required is False


def test_oar_1f_promotion_requires_validated_application_and_does_not_activate():
    validation = gsr.PostApplicationValidationRecord(
        validation_id="validation-oar",
        application_attempt_id="application-oar",
        focused_tests_passed=True,
        adjacent_regressions_passed=True,
        startup_smoke_passed=True,
        before_digests={"a.py": "before"},
        after_digests={"a.py": "after"},
        classification="application_validated",
    )
    request = gsr.make_capability_promotion_request(
        capability_id="language_claim_analysis",
        proposal_id="proposal-language-1",
        application_attempt_id="application-oar",
        validation_id=validation.validation_id,
        requested_evidence_tier="available",
        sequence=40,
    )
    authorization = gsr.make_capability_promotion_authorization(request, issued_sequence=41)
    result = gsr.promote_validated_capability_evidence(request, authorization, validation, sequence=42)

    assert result.accepted
    assert result.available is True
    assert result.active is False
    assert result.activation_required is True
    assert result.consumed_authorization.consumed is True

    failed_validation = replace(validation, classification="application_failed_startup_check", rollback_required=True)
    failed = gsr.promote_validated_capability_evidence(request, authorization, failed_validation, sequence=42)
    assert failed.accepted is False
    assert failed.reason == "validated_application_required"


def test_oar_1g_1h_restart_recovery_and_live_activation_are_explicit():
    state = gsr.OARRuntimeState(
        runtime_state_id="state-oar",
        development_runtime_mode="development_runtime",
        pending_review_ids=("proposal-language-1",),
        available_capability_ids=("language_claim_analysis",),
    )
    shutdown = gsr.shutdown_oar_runtime_cleanly(state, checkpoint_id="checkpoint-oar")
    recovered = gsr.recover_oar_runtime_after_restart(shutdown, integrity_valid=True)
    ok, reason, live = gsr.activate_oar_live_runtime(recovered, capability_ids=("language_claim_analysis",))

    assert shutdown.development_runtime_mode == "stopped"
    assert shutdown.live_runtime_mode == "stopped"
    assert recovered.automatic_resume_performed is False
    assert recovered.development_runtime_mode == "stopped"
    assert ok is True
    assert reason == "live_runtime_started_with_explicit_activation"
    assert live.live_runtime_mode == "live_runtime"
    assert live.active_capability_ids == ("language_claim_analysis",)

    rollback = replace(recovered, rollback_required_ids=("application-oar",))
    ok, reason, _ = gsr.activate_oar_live_runtime(rollback, capability_ids=("language_claim_analysis",))
    assert ok is False
    assert reason == "rollback_required"
