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


def test_oar_live_development_bridge_registers_approved_mission_without_starting_runtime():
    compiled, approval = _compiled_mission()
    state = gsr.OARRuntimeState(runtime_state_id="state-live-bridge")

    registered = gsr.register_approved_mission_for_development(state, compiled.compiled_objective, approval, sequence=50)

    assert registered.accepted is True
    assert registered.mission_registered is True
    assert registered.development_runtime_started is False
    assert registered.proposal_created is False
    assert registered.source_application_performed is False
    assert registered.capability_activated is False
    assert registered.automatic_continuation is False
    assert registered.state.development_runtime_mode == "stopped"
    assert registered.state.active_mission_id == compiled.compiled_objective.compiled_objective_id
    assert registered.state.approved_mission_ids == (compiled.compiled_objective.compiled_objective_id,)

    duplicate = gsr.register_approved_mission_for_development(registered.state, compiled.compiled_objective, approval, sequence=51)
    assert duplicate.accepted is False
    assert duplicate.reason == "duplicate_mission_approval"

    declined = replace(approval, operator_disposition="declined", starts_exactly_one_mission=False)
    denied = gsr.register_approved_mission_for_development(state, compiled.compiled_objective, declined, sequence=50)
    assert denied.accepted is False
    assert denied.reason == "mission_not_approved"


def test_oar_live_development_bridge_runs_one_cycle_and_queues_one_proposal_then_pauses():
    compiled, approval = _compiled_mission()
    state = gsr.OARRuntimeState(runtime_state_id="state-live-bridge")
    registered = gsr.register_approved_mission_for_development(state, compiled.compiled_objective, approval, sequence=50)

    cycle = gsr.run_one_oar_development_runtime_cycle(registered.state, compiled.compiled_objective, sequence=60)

    assert cycle.accepted is True
    assert cycle.development_runtime_started is True
    assert cycle.development_runtime_paused is True
    assert cycle.proposal_created is True
    assert cycle.proposal_queued is True
    assert cycle.second_cycle_started is False
    assert cycle.source_application_performed is False
    assert cycle.capability_promoted is False
    assert cycle.capability_activated is False
    assert cycle.provider_called is False
    assert cycle.model_invoked is False
    assert cycle.automatic_continuation is False
    assert cycle.state.development_runtime_mode == "paused"
    assert cycle.review_item is not None
    assert cycle.review_item.review_item_id in cycle.state.pending_review_ids
    assert cycle.review_item.parent_mission_id == compiled.compiled_objective.compiled_objective_id
    assert cycle.review_item.current_blocker == cycle.selected_capability_id
    assert cycle.review_item.sandbox_results["classification"] == "not_yet_executed"
    assert cycle.review_item.rollback_status == "not_required_no_source_application"

    second = gsr.run_one_oar_development_runtime_cycle(cycle.state, compiled.compiled_objective, sequence=60)
    assert second.accepted is False
    assert second.reason == "development_cycle_already_completed"

    recovered = gsr.recover_oar_runtime_after_restart(cycle.state, integrity_valid=True)
    assert recovered.development_runtime_mode == "stopped"
    duplicate_after_restart = gsr.run_one_oar_development_runtime_cycle(recovered, compiled.compiled_objective, sequence=61)
    assert duplicate_after_restart.accepted is False
    assert duplicate_after_restart.reason == "development_cycle_already_completed"


def _live_bridge_cycle() -> tuple[gsr.OARRuntimeState, gsr.OperatorReviewItem]:
    compiled, approval = _compiled_mission()
    state = gsr.OARRuntimeState(runtime_state_id="state-live-bridge")
    registered = gsr.register_approved_mission_for_development(state, compiled.compiled_objective, approval, sequence=50)
    cycle = gsr.run_one_oar_development_runtime_cycle(registered.state, compiled.compiled_objective, sequence=60)
    assert cycle.accepted is True
    assert cycle.review_item is not None
    return cycle.state, cycle.review_item


def test_live_2a_exact_queued_proposal_executes_one_fixture_and_queues_evidence():
    state, item = _live_bridge_cycle()
    authorization = gsr.make_live_fixture_execution_authorization(
        item,
        operator_identity="operator",
        issued_sequence=70,
        expiration_sequence=75,
    )

    result = gsr.execute_live_fixture_proposal(state, item, authorization, sequence=70)

    assert result.accepted is True
    assert result.reason == "fixture_execution_evidence_queued"
    assert result.authorization_consumed is True
    assert authorization.consumed is False
    assert result.consumed_authorization is not None
    assert result.consumed_authorization.consumed is True
    assert result.execution_performed is True
    assert result.evidence_item_queued is True
    assert result.runtime_paused is True
    assert result.tracked_source_mutated is False
    assert result.capability_activated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.automatic_continuation is False
    assert result.sandbox_result is not None
    assert result.sandbox_result.cleanup_verified is True
    assert result.sandbox_result.live_source_unchanged is True
    assert result.sandbox_evaluation is not None
    assert result.sandbox_evaluation.accepted_for_operator_review is True
    assert result.sandbox_evaluation.classification == "execution_succeeded"
    assert result.evidence_review_item is not None
    assert result.evidence_review_item.parent_review_item_id == item.review_item_id
    assert result.evidence_review_item.proposal_id == item.proposal_id
    assert result.evidence_review_item.exact_path == "fixture_capability_contract.py"
    assert result.evidence_review_item.cleanup_result == "verified"
    assert result.evidence_review_item.capability_remains_inactive is True
    assert result.evidence_review_item.tracked_source_unchanged is True
    assert result.evidence_review_item.application_performed is False
    assert result.evidence_review_item.automatic_continuation is False


def test_live_2a_mismatch_fails_before_authorization_consumption_and_restart_denies_duplicate():
    state, item = _live_bridge_cycle()
    authorization = gsr.make_live_fixture_execution_authorization(
        item,
        operator_identity="operator",
        issued_sequence=70,
        expiration_sequence=75,
    )
    wrong = replace(authorization, artifact_chain_digest="other-digest")

    denied = gsr.execute_live_fixture_proposal(state, item, wrong, sequence=70)
    assert denied.accepted is False
    assert denied.reason == "wrong_artifact_chain_digest"
    assert denied.authorization_consumed is False
    assert denied.execution_performed is False
    assert denied.consumed_authorization is None

    result = gsr.execute_live_fixture_proposal(state, item, authorization, sequence=70)
    assert result.accepted is True
    recovered = gsr.recover_oar_runtime_after_restart(result.state, integrity_valid=True)
    duplicate = gsr.execute_live_fixture_proposal(recovered, item, replace(authorization, consumed=True), sequence=71)
    assert duplicate.accepted is False
    assert duplicate.reason == "fixture_execution_already_completed"
    assert duplicate.execution_performed is False


def _live_2a_evidence() -> tuple[gsr.OARRuntimeState, gsr.OperatorReviewItem, gsr.LiveFixtureExecutionEvidenceItem]:
    state, item = _live_bridge_cycle()
    authorization = gsr.make_live_fixture_execution_authorization(
        item,
        operator_identity="operator",
        issued_sequence=70,
        expiration_sequence=75,
    )
    result = gsr.execute_live_fixture_proposal(state, item, authorization, sequence=70)
    assert result.accepted is True
    assert result.evidence_review_item is not None
    return result.state, item, result.evidence_review_item


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _digest(path: str) -> str:
    return hashlib.sha256((_repo() / path).read_bytes()).hexdigest()


def test_live_2b1_current_fixture_proposal_returns_fixture_only_readiness_without_application():
    state, item, evidence = _live_2a_evidence()
    mapping = gsr.make_live_tracked_source_target_mapping(item)
    request = gsr.make_live_tracked_source_preflight_request(
        item,
        evidence,
        mapping,
        repository_identity=str(_repo()),
        branch_identity="codex/delta-cognitive-core",
        requested_sequence=80,
    )
    authorization = gsr.make_live_tracked_source_preflight_authorization(
        request,
        operator_identity="operator",
        issued_sequence=80,
        expiration_sequence=85,
    )

    result = gsr.execute_live_tracked_source_preflight(
        state,
        item,
        evidence,
        request,
        authorization,
        sequence=80,
        repository_root=_repo(),
        current_branch="codex/delta-cognitive-core",
    )

    assert result.accepted is True
    assert result.reason == "fixture_only_no_tracked_target"
    assert result.authorization_consumed is True
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.source_read is False
    assert result.source_written is False
    assert result.patch_applied is False
    assert result.capability_activated is False
    assert result.git_operation_performed is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.automatic_continuation is False
    assert result.evidence.eligibility_classification == "fixture_only_no_tracked_target"
    assert result.evidence.proposed_tracked_target == ""
    assert result.evidence.application_not_performed is True
    assert result.evidence.capability_not_activated is True
    assert result.evidence_review_item["status"] == "readiness_queued"
    assert result.evidence_review_item["eligibility_classification"] == "fixture_only_no_tracked_target"


def test_live_2b1_explicit_tracked_mapping_can_be_represented_without_authorizing_application():
    state, item, evidence = _live_2a_evidence()
    target = "DELTA.py"
    mapping = gsr.make_live_tracked_source_target_mapping(
        item,
        tracked_target_path=target,
        mapping_origin="explicit_operator_mapping",
        expected_precondition_digest=_digest(target),
        application_payload_digest="a" * 64,
        rollback_plan_present=True,
        explicit_operator_mapping=True,
    )
    request = gsr.make_live_tracked_source_preflight_request(
        item,
        evidence,
        mapping,
        repository_identity=str(_repo()),
        branch_identity="codex/delta-cognitive-core",
        requested_sequence=80,
    )
    authorization = gsr.make_live_tracked_source_preflight_authorization(request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)

    result = gsr.execute_live_tracked_source_preflight(state, item, evidence, request, authorization, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")

    assert result.accepted is True
    assert result.reason == "eligible_for_exact_application_authorization"
    assert result.source_read is True
    assert result.source_written is False
    assert result.evidence.proposed_tracked_target == target
    assert result.evidence.tracked_file_status == "tracked"
    assert result.evidence.observed_precondition_digest == _digest(target)
    assert result.evidence.application_payload_status == "present"
    assert result.evidence.rollback_plan_status == "present"
    assert result.evidence.next_authorization_required == "LIVE-2B2 exact tracked-source application authorization"


def test_live_2b1_does_not_infer_target_from_architecture_metadata_and_denies_stale_or_bad_inputs_before_or_during_preflight():
    state, item, evidence = _live_2a_evidence()
    assert any("gsr_a_governed_self_regulation.py" in option.get("affected_subsystems", ()) for option in item.architecture_alternatives)

    mapping = gsr.make_live_tracked_source_target_mapping(item)
    request = gsr.make_live_tracked_source_preflight_request(item, evidence, mapping, repository_identity=str(_repo()), branch_identity="codex/delta-cognitive-core", requested_sequence=80)
    authorization = gsr.make_live_tracked_source_preflight_authorization(request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)
    fixture_only = gsr.execute_live_tracked_source_preflight(state, item, evidence, request, authorization, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert fixture_only.reason == "fixture_only_no_tracked_target"
    assert fixture_only.evidence.proposed_tracked_target == ""

    wrong_request = replace(request, artifact_chain_digest="other-chain")
    wrong = gsr.execute_live_tracked_source_preflight(state, item, evidence, wrong_request, authorization, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert wrong.accepted is False
    assert wrong.reason == "artifact_chain_mismatch"
    assert wrong.authorization_consumed is False
    assert wrong.consumed_authorization is None

    stale_mapping = gsr.make_live_tracked_source_target_mapping(
        item,
        tracked_target_path="DELTA.py",
        mapping_origin="explicit_operator_mapping",
        expected_precondition_digest="b" * 64,
        application_payload_digest="a" * 64,
        rollback_plan_present=True,
        explicit_operator_mapping=True,
    )
    stale_request = gsr.make_live_tracked_source_preflight_request(item, evidence, stale_mapping, repository_identity=str(_repo()), branch_identity="codex/delta-cognitive-core", requested_sequence=80)
    stale_auth = gsr.make_live_tracked_source_preflight_authorization(stale_request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)
    stale = gsr.execute_live_tracked_source_preflight(state, item, evidence, stale_request, stale_auth, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert stale.accepted is True
    assert stale.reason == "source_digest_stale"
    assert stale.authorization_consumed is True
    assert stale.source_read is True


def test_live_2b1_repository_branch_path_worktree_payload_and_reuse_denials_are_stable():
    state, item, evidence = _live_2a_evidence()
    target = "DELTA.py"
    mapping = gsr.make_live_tracked_source_target_mapping(
        item,
        tracked_target_path=target,
        mapping_origin="explicit_operator_mapping",
        expected_precondition_digest=_digest(target),
        application_payload_digest="",
        rollback_plan_present=False,
        explicit_operator_mapping=True,
    )
    request = gsr.make_live_tracked_source_preflight_request(item, evidence, mapping, repository_identity=str(_repo()), branch_identity="codex/delta-cognitive-core", requested_sequence=80)
    authorization = gsr.make_live_tracked_source_preflight_authorization(request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)

    missing_payload = gsr.execute_live_tracked_source_preflight(state, item, evidence, request, authorization, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert missing_payload.reason == "application_payload_missing"
    assert missing_payload.evidence.application_payload_status == "missing"

    repo_mismatch = gsr.execute_live_tracked_source_preflight(state, item, evidence, request, authorization, sequence=80, repository_root=_repo().parent, current_branch="codex/delta-cognitive-core")
    assert repo_mismatch.reason == "repository_mismatch"
    branch_mismatch = gsr.execute_live_tracked_source_preflight(state, item, evidence, request, authorization, sequence=80, repository_root=_repo(), current_branch="other-branch")
    assert branch_mismatch.reason == "branch_mismatch"

    bad_path_mapping = replace(mapping, tracked_target_path="../escape.py", explicit_operator_mapping=True)
    bad_path_request = gsr.make_live_tracked_source_preflight_request(item, evidence, bad_path_mapping, repository_identity=str(_repo()), branch_identity="codex/delta-cognitive-core", requested_sequence=80)
    bad_path_auth = gsr.make_live_tracked_source_preflight_authorization(bad_path_request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)
    bad_path = gsr.execute_live_tracked_source_preflight(state, item, evidence, bad_path_request, bad_path_auth, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert bad_path.reason == "target_path_invalid"

    untracked_mapping = replace(mapping, tracked_target_path="fixture_capability_contract.py", application_payload_digest="a" * 64, rollback_plan_present=True, explicit_operator_mapping=True)
    untracked_request = gsr.make_live_tracked_source_preflight_request(item, evidence, untracked_mapping, repository_identity=str(_repo()), branch_identity="codex/delta-cognitive-core", requested_sequence=80)
    untracked_auth = gsr.make_live_tracked_source_preflight_authorization(untracked_request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)
    untracked = gsr.execute_live_tracked_source_preflight(state, item, evidence, untracked_request, untracked_auth, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert untracked.reason == "target_not_tracked"

    duplicate = gsr.execute_live_tracked_source_preflight(missing_payload.state, item, evidence, request, replace(authorization, consumed=True), sequence=81, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert duplicate.accepted is False
    assert duplicate.reason == "tracked_preflight_already_completed"


def _eligible_live_2b1(target: str = "DELTA.py") -> tuple[gsr.OARRuntimeState, gsr.LiveTrackedSourcePreflightResult]:
    state, item, evidence = _live_2a_evidence()
    mapping = gsr.make_live_tracked_source_target_mapping(
        item,
        tracked_target_path=target,
        mapping_origin="explicit_operator_mapping",
        expected_precondition_digest=_digest(target),
        application_payload_digest="a" * 64,
        rollback_plan_present=True,
        explicit_operator_mapping=True,
    )
    request = gsr.make_live_tracked_source_preflight_request(item, evidence, mapping, repository_identity=str(_repo()), branch_identity="codex/delta-cognitive-core", requested_sequence=80)
    authorization = gsr.make_live_tracked_source_preflight_authorization(request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)
    result = gsr.execute_live_tracked_source_preflight(state, item, evidence, request, authorization, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    assert result.accepted is True
    assert result.reason == "eligible_for_exact_application_authorization"
    return result.state, result


def _copy_target_to_isolated_repo(tmp_path: Path, target: str = "DELTA.py") -> Path:
    isolated = tmp_path / "isolated_repo"
    target_path = isolated / target
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes((_repo() / target).read_bytes())
    return isolated


def _live_2b2_request(preflight: gsr.LiveTrackedSourcePreflightResult, isolated: Path, *, text: str = "# governed live application proof\n") -> gsr.LiveTrackedSourceApplicationRequest:
    target = preflight.evidence.proposed_tracked_target
    return gsr.make_live_tracked_source_application_request(
        preflight,
        isolated_repository_identity=str(isolated.resolve()),
        reviewed_text_by_target={target: text},
        validation_commands=("focused-live-application",),
        requested_sequence=90,
    )


def test_live_2b2_authorization_is_exact_one_shot_and_does_not_write_before_consumption(tmp_path):
    _, preflight = _eligible_live_2b1()
    isolated = _copy_target_to_isolated_repo(tmp_path)
    request = _live_2b2_request(preflight, isolated)
    authorization = gsr.make_live_tracked_source_application_authorization(request, operator_identity="operator", issued_sequence=90, expiration_sequence=95)

    wrong = replace(authorization, authorized_payload_digest="b" * 64)
    denied = gsr.execute_live_tracked_source_application(
        preflight.state,
        preflight,
        request,
        wrong,
        isolated_root=isolated,
        validation_results={"focused-live-application": True},
        sequence=90,
    )

    assert denied.accepted is False
    assert denied.reason == "patch_payload_mismatch"
    assert denied.authorization_consumed is False
    assert denied.application_performed is False
    assert (isolated / "DELTA.py").read_bytes() == (_repo() / "DELTA.py").read_bytes()

    expired = replace(authorization, expiration_sequence=89)
    denied_expired = gsr.execute_live_tracked_source_application(
        preflight.state,
        preflight,
        request,
        expired,
        isolated_root=isolated,
        validation_results={"focused-live-application": True},
        sequence=90,
    )
    assert denied_expired.reason == "application_authorization_expired"
    assert denied_expired.authorization_consumed is False


def test_live_2b3_2b4_success_applies_exact_change_in_isolated_copy_and_queues_evidence(tmp_path):
    _, preflight = _eligible_live_2b1()
    isolated = _copy_target_to_isolated_repo(tmp_path)
    request = _live_2b2_request(preflight, isolated)
    authorization = gsr.make_live_tracked_source_application_authorization(request, operator_identity="operator", issued_sequence=90, expiration_sequence=95)

    result = gsr.execute_live_tracked_source_application(
        preflight.state,
        preflight,
        request,
        authorization,
        isolated_root=isolated,
        validation_results={"focused-live-application": True},
        sequence=90,
    )

    assert result.accepted is True
    assert result.reason == "application_validated"
    assert result.authorization_consumed is True
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.application_performed is True
    assert result.validation_succeeded is True
    assert result.rollback_performed is False
    assert result.active_worktree_mutated is False
    assert result.capability_activated is False
    assert result.git_operation_performed is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.automatic_continuation is False
    assert (isolated / "DELTA.py").read_text(encoding="utf-8") == "# governed live application proof\n"
    assert (_repo() / "DELTA.py").read_bytes() != (isolated / "DELTA.py").read_bytes()
    assert result.evidence.classification == "application_validated"
    assert result.evidence_review_item["status"] == "application_evidence_queued"

    duplicate = gsr.execute_live_tracked_source_application(
        result.state,
        preflight,
        request,
        replace(authorization, consumed=True),
        isolated_root=isolated,
        validation_results={"focused-live-application": True},
        sequence=91,
    )
    assert duplicate.accepted is False
    assert duplicate.reason == "tracked_application_already_completed"


def test_live_2b4_failed_validation_rolls_back_exact_original_hash(tmp_path):
    _, preflight = _eligible_live_2b1()
    isolated = _copy_target_to_isolated_repo(tmp_path)
    original_digest = hashlib.sha256((isolated / "DELTA.py").read_bytes()).hexdigest()
    request = _live_2b2_request(preflight, isolated)
    authorization = gsr.make_live_tracked_source_application_authorization(request, operator_identity="operator", issued_sequence=90, expiration_sequence=95)

    result = gsr.execute_live_tracked_source_application(
        preflight.state,
        preflight,
        request,
        authorization,
        isolated_root=isolated,
        validation_results={"focused-live-application": False},
        sequence=90,
    )

    assert result.accepted is False
    assert result.reason == "application_rolled_back"
    assert result.authorization_consumed is True
    assert result.application_performed is True
    assert result.rollback_performed is True
    assert hashlib.sha256((isolated / "DELTA.py").read_bytes()).hexdigest() == original_digest
    assert result.evidence.rollback_digests == result.evidence.pre_application_digests


def _validated_application(tmp_path: Path) -> tuple[gsr.OARRuntimeState, gsr.LiveTrackedSourceApplicationEvidence]:
    _, preflight = _eligible_live_2b1()
    isolated = _copy_target_to_isolated_repo(tmp_path)
    request = _live_2b2_request(preflight, isolated)
    authorization = gsr.make_live_tracked_source_application_authorization(request, operator_identity="operator", issued_sequence=90, expiration_sequence=95)
    result = gsr.execute_live_tracked_source_application(
        preflight.state,
        preflight,
        request,
        authorization,
        isolated_root=isolated,
        validation_results={"focused-live-application": True},
        sequence=90,
    )
    assert result.accepted is True
    return result.state, result.evidence


def test_live_2c_promotion_is_operator_controlled_tiered_and_does_not_activate(tmp_path):
    state, evidence = _validated_application(tmp_path)
    request = gsr.make_live_capability_promotion_request(
        evidence,
        capability_id="language_claim_representation",
        capability_version="1",
        requested_from_tier="integration_tested",
        requested_to_tier="tracked_source_validated",
        requested_sequence=100,
    )
    authorization = gsr.make_live_capability_promotion_authorization(request, issued_sequence=100, expiration_sequence=105)
    result = gsr.promote_live_capability_evidence(state, evidence, request, authorization, sequence=100)

    assert result.accepted is True
    assert result.promoted_tier == "tracked_source_validated"
    assert result.capability_available is False
    assert result.capability_active is False
    assert result.activation_required is True
    assert result.authorization_consumed is True
    assert result.consumed_authorization.consumed is True
    assert "language_claim_representation" not in result.state.active_capability_ids

    skip = gsr.make_live_capability_promotion_request(
        evidence,
        capability_id="language_claim_representation",
        capability_version="1",
        requested_from_tier="integration_tested",
        requested_to_tier="available",
        requested_sequence=101,
    )
    skip_auth = gsr.make_live_capability_promotion_authorization(skip, issued_sequence=101, expiration_sequence=106)
    denied = gsr.promote_live_capability_evidence(state, evidence, skip, skip_auth, sequence=101)
    assert denied.accepted is False
    assert denied.reason == "evidence_tier_skip_denied"

    failed = replace(evidence, classification="application_rolled_back", rollback_performed=True)
    denied_failed = gsr.promote_live_capability_evidence(state, failed, request, authorization, sequence=100)
    assert denied_failed.reason == "validated_application_required"


def _available_capability(tmp_path: Path) -> tuple[gsr.OARRuntimeState, gsr.LiveTrackedSourceApplicationEvidence, gsr.LiveCapabilityPromotionResult]:
    state, evidence = _validated_application(tmp_path)
    tiers = (
        ("integration_tested", "tracked_source_validated"),
        ("tracked_source_validated", "operator_approved"),
        ("operator_approved", "available"),
    )
    promotion = None
    for offset, (src, dst) in enumerate(tiers):
        request = gsr.make_live_capability_promotion_request(
            evidence,
            capability_id="language_claim_representation",
            capability_version="1",
            requested_from_tier=src,
            requested_to_tier=dst,
            requested_sequence=100 + offset,
        )
        authorization = gsr.make_live_capability_promotion_authorization(request, issued_sequence=100 + offset, expiration_sequence=110)
        promotion = gsr.promote_live_capability_evidence(state, evidence, request, authorization, sequence=100 + offset)
        assert promotion.accepted is True
        state = promotion.state
    assert promotion.capability_available is True
    return state, evidence, promotion


def test_live_2d_activation_requires_separate_authorization_and_can_deactivate(tmp_path):
    state, _, promotion = _available_capability(tmp_path)
    request = gsr.make_live_capability_activation_request(
        promotion,
        capability_version="1",
        runtime_checkpoint_id="checkpoint-live-2d",
        allowed_runtime_behavior=("fixture_verification_only",),
        deactivation_plan_digest="deactivate-" + "a" * 16,
        requested_sequence=120,
    )
    wrong = gsr.make_live_capability_activation_authorization(request, issued_sequence=120, expiration_sequence=125)
    wrong = replace(wrong, application_authorized=True)

    denied = gsr.activate_live_capability(state, request, wrong, sequence=120, verification_passed=True)
    assert denied.accepted is False
    assert denied.reason == "forbidden_authority"
    assert denied.authorization_consumed is False

    authorization = gsr.make_live_capability_activation_authorization(request, issued_sequence=120, expiration_sequence=125)
    result = gsr.activate_live_capability(state, request, authorization, sequence=120, verification_passed=True, deactivate_after_verification=True)

    assert result.accepted is True
    assert result.reason == "activation_verified"
    assert result.activation_performed is True
    assert result.deactivation_verified is True
    assert result.authorization_consumed is True
    assert result.consumed_authorization.consumed is True
    assert result.application_performed is False
    assert result.git_operation_performed is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.automatic_continuation is False
    assert "language_claim_representation" not in result.state.active_capability_ids
    assert "language_claim_representation" in result.state.activated_capability_ids


def _active_capability_for_live_3(tmp_path: Path) -> tuple[
    gsr.CompiledMissionObjective,
    gsr.OperatorReviewItem,
    gsr.OARRuntimeState,
    gsr.LiveTrackedSourceApplicationEvidence,
    gsr.LiveCapabilityPromotionResult,
    gsr.LiveCapabilityActivationEvidence,
]:
    compiled, approval = _compiled_mission()
    state = gsr.OARRuntimeState(runtime_state_id="state-live-bridge")
    registered = gsr.register_approved_mission_for_development(state, compiled.compiled_objective, approval, sequence=50)
    cycle = gsr.run_one_oar_development_runtime_cycle(registered.state, compiled.compiled_objective, sequence=60)
    assert cycle.review_item is not None
    item = cycle.review_item
    fixture_auth = gsr.make_live_fixture_execution_authorization(item, operator_identity="operator", issued_sequence=70, expiration_sequence=75)
    fixture = gsr.execute_live_fixture_proposal(cycle.state, item, fixture_auth, sequence=70)
    assert fixture.evidence_review_item is not None
    target = "DELTA.py"
    mapping = gsr.make_live_tracked_source_target_mapping(
        item,
        tracked_target_path=target,
        mapping_origin="explicit_operator_mapping",
        expected_precondition_digest=_digest(target),
        application_payload_digest="a" * 64,
        rollback_plan_present=True,
        explicit_operator_mapping=True,
    )
    preflight_request = gsr.make_live_tracked_source_preflight_request(
        item,
        fixture.evidence_review_item,
        mapping,
        repository_identity=str(_repo()),
        branch_identity="codex/delta-cognitive-core",
        requested_sequence=80,
    )
    preflight_auth = gsr.make_live_tracked_source_preflight_authorization(preflight_request, operator_identity="operator", issued_sequence=80, expiration_sequence=85)
    preflight = gsr.execute_live_tracked_source_preflight(fixture.state, item, fixture.evidence_review_item, preflight_request, preflight_auth, sequence=80, repository_root=_repo(), current_branch="codex/delta-cognitive-core")
    isolated = _copy_target_to_isolated_repo(tmp_path)
    app_request = _live_2b2_request(preflight, isolated)
    app_auth = gsr.make_live_tracked_source_application_authorization(app_request, operator_identity="operator", issued_sequence=90, expiration_sequence=95)
    application = gsr.execute_live_tracked_source_application(preflight.state, preflight, app_request, app_auth, isolated_root=isolated, validation_results={"focused-live-application": True}, sequence=90)
    assert application.evidence is not None
    state = application.state
    evidence = application.evidence
    promotion = None
    for offset, (src, dst) in enumerate((
        ("integration_tested", "tracked_source_validated"),
        ("tracked_source_validated", "operator_approved"),
        ("operator_approved", "available"),
    )):
        promotion_request = gsr.make_live_capability_promotion_request(
            evidence,
            capability_id=item.current_blocker,
            capability_version="1",
            requested_from_tier=src,
            requested_to_tier=dst,
            requested_sequence=100 + offset,
        )
        promotion_auth = gsr.make_live_capability_promotion_authorization(promotion_request, issued_sequence=100 + offset, expiration_sequence=110)
        promotion = gsr.promote_live_capability_evidence(state, evidence, promotion_request, promotion_auth, sequence=100 + offset)
        assert promotion.accepted is True
        state = promotion.state
    activation_request = gsr.make_live_capability_activation_request(
        promotion,
        capability_version="1",
        runtime_checkpoint_id="checkpoint-live-3",
        allowed_runtime_behavior=("one_bounded_mission_progress_cycle",),
        deactivation_plan_digest="deactivate-" + "b" * 16,
        requested_sequence=120,
    )
    activation_auth = gsr.make_live_capability_activation_authorization(activation_request, issued_sequence=120, expiration_sequence=125)
    activation = gsr.activate_live_capability(state, activation_request, activation_auth, sequence=120, verification_passed=True, deactivate_after_verification=False)
    assert activation.accepted is True
    assert activation.evidence is not None
    return compiled.compiled_objective, item, activation.state, evidence, promotion, activation.evidence


def test_live_3_resumes_exact_parent_mission_and_records_one_progress_item(tmp_path):
    compiled, item, state, application_evidence, promotion, activation_evidence = _active_capability_for_live_3(tmp_path)
    checkpoint = gsr.make_live_parent_mission_checkpoint(compiled, item, runtime_checkpoint_id="checkpoint-live-3")
    request = gsr.make_live_mission_resumption_request(
        checkpoint,
        activation_evidence,
        application_evidence_id=application_evidence.application_evidence_id,
        promoted_tier=promotion.promoted_tier,
        requested_sequence=130,
    )

    result = gsr.resume_parent_mission_once_live(state, compiled, checkpoint, activation_evidence, request, sequence=130, blocker_closed_evidence=True)

    assert result.accepted is True
    assert result.reason == "blocker_closed_resume_mission"
    assert result.blocker_closed is True
    assert result.mission_progress_performed is True
    assert result.progress_evidence.original_parent_mission == compiled.original_operator_mission
    assert result.progress_evidence.parent_mission_unchanged is True
    assert result.progress_evidence.mission_work_item
    assert result.evidence_review_item["status"] == "mission_progress_queued"
    assert result.state.development_runtime_mode == "paused"
    assert result.tracked_source_mutated is False
    assert result.capability_campaign_started is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.automatic_continuation is False

    duplicate = gsr.resume_parent_mission_once_live(result.state, compiled, checkpoint, activation_evidence, request, sequence=131, blocker_closed_evidence=True)
    assert duplicate.accepted is False
    assert duplicate.reason == "mission_resumption_already_completed"


def test_live_3_denies_inactive_or_stale_or_mismatched_parent_mission(tmp_path):
    compiled, item, state, application_evidence, promotion, activation_evidence = _active_capability_for_live_3(tmp_path)
    checkpoint = gsr.make_live_parent_mission_checkpoint(compiled, item, runtime_checkpoint_id="checkpoint-live-3")
    request = gsr.make_live_mission_resumption_request(
        checkpoint,
        activation_evidence,
        application_evidence_id=application_evidence.application_evidence_id,
        promoted_tier=promotion.promoted_tier,
        requested_sequence=130,
    )

    inactive_state = replace(state, active_capability_ids=())
    inactive = gsr.resume_parent_mission_once_live(inactive_state, compiled, checkpoint, activation_evidence, request, sequence=130, blocker_closed_evidence=True)
    assert inactive.accepted is False
    assert inactive.reason == "activation_not_sufficient"

    stale_request = replace(request, runtime_checkpoint_id="old-checkpoint")
    stale = gsr.resume_parent_mission_once_live(state, compiled, checkpoint, activation_evidence, stale_request, sequence=130, blocker_closed_evidence=True)
    assert stale.accepted is False
    assert stale.reason == "mission_checkpoint_stale"

    rewritten = replace(compiled, original_operator_mission="do an easier mission")
    mismatch = gsr.resume_parent_mission_once_live(state, rewritten, checkpoint, activation_evidence, request, sequence=130, blocker_closed_evidence=True)
    assert mismatch.accepted is False
    assert mismatch.reason == "mission_identity_mismatch"


def test_live_3_blocker_evidence_and_new_blocker_remain_bounded(tmp_path):
    compiled, item, state, application_evidence, promotion, activation_evidence = _active_capability_for_live_3(tmp_path)
    checkpoint = gsr.make_live_parent_mission_checkpoint(compiled, item, runtime_checkpoint_id="checkpoint-live-3")
    request = gsr.make_live_mission_resumption_request(
        checkpoint,
        activation_evidence,
        application_evidence_id=application_evidence.application_evidence_id,
        promoted_tier=promotion.promoted_tier,
        requested_sequence=130,
    )

    not_closed = gsr.resume_parent_mission_once_live(state, compiled, checkpoint, activation_evidence, request, sequence=130, blocker_closed_evidence=False)
    assert not_closed.accepted is False
    assert not_closed.reason == "blocker_not_closed"
    assert not_closed.mission_progress_performed is False
    assert not_closed.capability_campaign_started is False

    new_blocker = gsr.resume_parent_mission_once_live(state, compiled, checkpoint, activation_evidence, request, sequence=130, blocker_closed_evidence=True, new_blocker_id="bounded_evidence_source_parser")
    assert new_blocker.accepted is True
    assert new_blocker.reason == "new_capability_gap_detected"
    assert new_blocker.progress_evidence.new_blocker_id == "bounded_evidence_source_parser"
    assert new_blocker.capability_campaign_started is False
    assert new_blocker.automatic_continuation is False

    broad = replace(request, another_capability_campaign_requested=True)
    denied = gsr.resume_parent_mission_once_live(state, compiled, checkpoint, activation_evidence, broad, sequence=130, blocker_closed_evidence=True)
    assert denied.accepted is False
    assert denied.reason == "operator_decision_required"


def _live_4_request() -> tuple[gsr.OARRuntimeState, gsr.CompiledMissionObjective, gsr.LiveMultiCycleMissionRequest]:
    compiled_result, _approval = _compiled_mission()
    compiled = compiled_result.compiled_objective
    state = gsr.OARRuntimeState(runtime_state_id="state-live-4", approved_mission_ids=(compiled.compiled_objective_id,), active_mission_id=compiled.compiled_objective_id)
    request = gsr.make_live_multi_cycle_mission_request(compiled, starting_checkpoint_id="checkpoint-live-4", requested_sequence=140)
    return state, compiled, request


def test_live_4_three_cycle_success_preserves_one_parent_mission_and_limits():
    state, compiled, request = _live_4_request()
    cycles = (
        gsr.LiveMissionCycleInput(1, "checkpoint-live-4-a", "inspect bounded claim", "claim represented"),
        gsr.LiveMissionCycleInput(2, "checkpoint-live-4-b", "compare evidence link", "evidence link checked"),
        gsr.LiveMissionCycleInput(3, "checkpoint-live-4-c", "summarize bounded result", "mission work complete"),
    )

    result = gsr.run_live_multi_cycle_mission(state, compiled, request, cycles)

    assert result.accepted is True
    assert result.reason == "complete_mission"
    assert result.mission_completed is True
    assert len(result.cycle_records) == 3
    assert {record.parent_mission_id for record in result.cycle_records} == {compiled.compiled_objective_id}
    assert all(record.original_parent_mission == compiled.original_operator_mission for record in result.cycle_records)
    assert result.capability_campaign_count == 0
    assert result.application_count == 0
    assert result.activation_count == 0
    assert result.state.development_runtime_mode == "paused"
    assert result.tracked_source_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.automatic_continuation is False


def test_live_4_evidenced_blocker_can_trigger_one_campaign_and_resume():
    state, compiled, request = _live_4_request()
    cycles = (
        gsr.LiveMissionCycleInput(1, "checkpoint-live-4-a", "attempt source-bound claim", "blocked by parser", blocker_id="bounded_source_parser", blocker_evidenced=True, capability_campaign_approved=True, capability_closes_blocker=True),
        gsr.LiveMissionCycleInput(2, "checkpoint-live-4-b", "resume after parser", "progress after approved capability"),
    )

    result = gsr.run_live_multi_cycle_mission(state, compiled, request, cycles)

    assert result.accepted is True
    assert result.cycle_records[0].decision == "resume_after_capability_approval"
    assert result.cycle_records[0].capability_campaign_started is True
    assert result.cycle_records[0].capability_integrated is True
    assert result.capability_campaign_count == 1
    assert result.application_count == 1
    assert result.activation_count == 1
    assert result.cycle_records[1].mission_resumed is True

    second_blocker = cycles + (
        gsr.LiveMissionCycleInput(3, "checkpoint-live-4-c", "second blocker", "blocked again", blocker_id="another_gap", blocker_evidenced=True, capability_campaign_approved=True, capability_closes_blocker=True),
    )
    exhausted = gsr.run_live_multi_cycle_mission(state, compiled, request, second_blocker)
    assert exhausted.reason == "complete_budget_exhausted"
    assert exhausted.capability_campaign_count == 1


def test_live_4_rejection_stagnation_drift_and_scope_expansion_stop_cleanly():
    state, compiled, request = _live_4_request()

    rejected = gsr.run_live_multi_cycle_mission(
        state,
        compiled,
        request,
        (gsr.LiveMissionCycleInput(1, "checkpoint-live-4-a", "blocked work", "operator rejected", blocker_id="gap", blocker_evidenced=True, operator_rejected=True),),
    )
    assert rejected.reason == "pause_for_operator"
    assert rejected.capability_campaign_count == 0

    stagnation = gsr.run_live_multi_cycle_mission(
        state,
        compiled,
        request,
        (
            gsr.LiveMissionCycleInput(1, "checkpoint-live-4-a", "blocked work", "still blocked", blocker_id="gap", blocker_evidenced=True),
            gsr.LiveMissionCycleInput(2, "checkpoint-live-4-b", "retry blocked work", "still blocked", blocker_id="gap", blocker_evidenced=True),
        ),
    )
    assert stagnation.reason == "pause_for_operator"
    assert stagnation.automatic_continuation is False

    drift = gsr.run_live_multi_cycle_mission(
        state,
        compiled,
        request,
        (gsr.LiveMissionCycleInput(1, "checkpoint-live-4-a", "drift", "drift", parent_mission_override="different mission"),),
    )
    assert drift.accepted is False
    assert drift.reason == "suspend_scope_drift"

    broad = gsr.run_live_multi_cycle_mission(
        state,
        compiled,
        request,
        (gsr.LiveMissionCycleInput(1, "checkpoint-live-4-a", "needs scope", "scope expansion required", scope_expansion_required=True),),
    )
    assert broad.reason == "pause_for_operator"


def test_live_4_denies_bad_cycle_order_budget_and_forbidden_authority():
    state, compiled, request = _live_4_request()

    bad_order = gsr.run_live_multi_cycle_mission(
        state,
        compiled,
        request,
        (gsr.LiveMissionCycleInput(2, "checkpoint-live-4-b", "out of order", "bad"),),
    )
    assert bad_order.accepted is False
    assert bad_order.reason == "cycle_order_invalid"

    too_many = replace(request, maximum_mission_cycles=4)
    denied_budget = gsr.run_live_multi_cycle_mission(state, compiled, too_many, ())
    assert denied_budget.accepted is False
    assert denied_budget.reason == "budget_scope_invalid"

    forbidden = replace(request, provider_model_requested=True)
    denied_forbidden = gsr.run_live_multi_cycle_mission(state, compiled, forbidden, ())
    assert denied_forbidden.reason == "operator_decision_required"

    rewritten = replace(compiled, original_operator_mission="new mission")
    denied_drift = gsr.run_live_multi_cycle_mission(state, rewritten, request, ())
    assert denied_drift.reason == "mission_identity_mismatch"
