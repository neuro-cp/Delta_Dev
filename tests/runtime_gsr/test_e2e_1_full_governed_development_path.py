from __future__ import annotations

import hashlib
import multiprocessing
import threading
import tkinter as tk
from dataclasses import replace
from pathlib import Path

import DELTA
from orchestration.runtime import gsr_a_governed_self_regulation as gsr
from orchestration.runtime.e2e_1_durable_runtime_state import DurableRuntimeStateStore, default_clean_checkpoint_state


MISSION = "Improve demonstrated language comprehension and scholarly discussion ability."


def _mission_to_cde_chain():
    compilation_request = gsr.make_mission_compilation_request(
        MISSION,
        baseline_evaluation_id="baseline-scholar-language",
        requested_sequence=5000,
    )
    compilation_authorization = gsr.make_mission_compilation_authorization(compilation_request, issued_sequence=5001)
    compiled = gsr.compile_language_development_mission(compilation_request, compilation_authorization, sequence=5002)
    assert compiled.accepted
    approval = gsr.approve_compiled_mission(compiled.compiled_objective, operator_identity="operator", sequence=5003)

    cde_request = gsr.make_capability_development_mission_request(
        original_operator_wording=MISSION,
        intended_outcome="improve bounded scholarly-language analysis after evidence-backed capability development",
        domain="scholarly_language_discussion",
        constraints=("fixture_only", "operator_review_required", "no_network"),
        prohibited_outcomes=("autonomous_git", "capability_self_activation", "permission_expansion"),
        success_concept="first language blocker improved and mission resumed",
        requested_sequence=5010,
    )
    cde_authorization = gsr.make_capability_development_mission_authorization(cde_request, issued_sequence=5011, expiration_sequence=5100)
    mission = gsr.interpret_capability_development_mission(cde_request, cde_authorization, sequence=5012)
    graph = gsr.build_required_capability_graph(mission.mission)
    self_model = gsr.build_demonstrated_capability_self_model()
    analysis = gsr.analyze_capability_gaps(graph.graph, self_model, mission.mission)
    selection = gsr.select_capability_prerequisite(analysis, graph.graph)
    spec_request = gsr.make_capability_specification_request(mission.mission, selection, requested_sequence=5020)
    spec_authorization = gsr.make_capability_specification_authorization(spec_request, issued_sequence=5021, expiration_sequence=5100)
    spec = gsr.synthesize_capability_specification(mission.mission, graph.graph, self_model, selection, spec_request, spec_authorization, sequence=5022)
    options = gsr.generate_capability_architecture_options(spec.specification)
    architecture = gsr.select_minimum_viable_architecture(spec.specification, options)
    validation_plan = gsr.synthesize_capability_validation_plan(spec.specification, architecture)
    implementation_plan = gsr.synthesize_capability_implementation_plan(spec.specification, architecture, validation_plan)
    campaign = gsr.run_capability_implementation_campaign(spec.specification, architecture, validation_plan, implementation_plan, sequence=5030)
    promotion = gsr.analyze_capability_integration_and_promotion(spec.specification, campaign, operator_approved=True)
    state = gsr.make_recursive_mission_state(mission.mission, self_model, selection.selected_capability_id)
    invocation = gsr.invoke_capability_development_from_mission(state, selection, sequence=5040)
    resumed = gsr.resume_recursive_mission_after_approval(invocation.state, promotion)
    review = gsr.create_recursive_mission_review_package(resumed, mission.mission, graph.graph, self_model, spec.specification, options, architecture, campaign, promotion, gsr.resume_parent_mission_after_capability(mission.mission, promotion, analysis))
    return compiled, approval, mission, graph, self_model, analysis, selection, spec, options, architecture, validation_plan, implementation_plan, campaign, promotion, state, invocation, resumed, review


def _review_item(tmp_path: Path, compiled: gsr.MissionCompilationResult, spec: gsr.CapabilitySpecificationResult, options: gsr.CapabilityArchitectureOptionsResult, architecture: gsr.CapabilityArchitectureSelection) -> tuple[gsr.OperatorReviewItem, str]:
    target = tmp_path / "fixture_language_capability.py"
    target.write_text("def analyze(text):\n    return {'assertion': text}\n", encoding="utf-8")
    pre_hash = gsr.inspect_application_targets_read_only(tmp_path, ("fixture_language_capability.py",)).current_target_hashes["fixture_language_capability.py"]
    item = gsr.make_evaluation_review_item(
        parent_mission_id=compiled.compiled_objective.compiled_objective_id,
        compiled_objective_id=compiled.compiled_objective.compiled_objective_id,
        capability_gap_id=spec.specification.capability_id,
        proposal_id="proposal-e2e-language",
        parent_mission=MISSION,
        current_blocker="weak evidence versus assertion distinction",
        capability_specification=gsr.serialize(spec.specification),
        architecture_alternatives=tuple(options.options),
        selected_design=gsr.serialize(architecture),
        exact_affected_files=("fixture_language_capability.py",),
        full_patch_or_structured_change="replace exact fixture analyzer with evidence/assertion split",
        focused_tests=("fixture-focused",),
        adjacent_regressions=("fixture-adjacent",),
        sandbox_results={"classification": "passed", "cleanup": "verified"},
        score_change={"evidence_assertion_distinction": 0.2},
        artifact_chain_digest="chain-e2e-language",
        source_precondition_hashes={"fixture_language_capability.py": pre_hash},
        resources_used=({"identity": "baseline-scholar-language", "authority": "operator-approved fixture"},),
        model_provider_identity="none",
    )
    return item, pre_hash


def test_e2e_1_full_governed_path_through_tk_review_application_restart_and_activation(tmp_path: Path):
    thread_count_before = threading.active_count()
    child_processes_before = tuple(multiprocessing.active_children())
    compiled, approval, _mission, graph, self_model, analysis, selection, spec, options, architecture, validation_plan, implementation_plan, campaign, promotion, state, invocation, resumed, review = _mission_to_cde_chain()

    assert approval.starts_exactly_one_mission is True
    assert graph.accepted and len(graph.graph.nodes) <= 12
    assert all(
        "tracked_source_validated" not in tuple(capability.get("evidence_tiers", ()))
        or capability.get("checkpoint_commit")
        for capability in self_model.capabilities
    )
    assert selection.selected_gap_id == analysis.first_actionable_gap_id
    assert selection.selected_capability_id
    assert validation_plan.frozen_before_implementation is True
    assert implementation_plan.direct_source_mutation is False
    assert campaign.tracked_source_mutated is False
    assert invocation.accepted and invocation.active_campaigns == 1
    assert review.final_disposition in {"select_next_blocking_capability", "mission_feasible"}

    item, pre_hash = _review_item(tmp_path, compiled, spec, options, architecture)
    root = tk.Tk()
    root.withdraw()
    app = DELTA.DeltaApp.__new__(DELTA.DeltaApp)
    app.root = root
    try:
        outer = DELTA.ttk.Frame(root)
        outer.pack(fill=tk.BOTH, expand=True)
        app.notebook = DELTA.ttk.Notebook(outer)
        app.notebook.pack(fill=tk.BOTH, expand=True)
        app.evaluation_tab = DELTA.ttk.Frame(app.notebook, padding=10)
        app.notebook.add(app.evaluation_tab, text="Evaluation")
        app._build_evaluation_tab()
        app._set_evaluation_review_items([item])
        selected = app.evaluation_items.get_children()[0]
        app.evaluation_items.selection_set(selected)
        app._record_evaluation_disposition("accepted")
        assert len(app.evaluation_dispositions) == 1
        assert app.evaluation_dispositions[0]["operator_disposition"] == "accepted"
        assert app.evaluation_dispositions[0]["source_written"] is False
    finally:
        root.destroy()

    evaluation = gsr.SandboxEvidenceEvaluation(
        evaluation_id="eval-e2e",
        cycle_id="cycle-e2e",
        plan_id="plan-e2e",
        attempt_id="attempt-e2e",
        request_id="request-e2e",
        authorization_id="auth-e2e",
        evidence_digest="digest-e2e",
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
        record_id="record-e2e",
        evaluation_id=evaluation.evaluation_id,
        disposition_request_id="disp-request-e2e",
        disposition_id=app.evaluation_dispositions[0]["disposition_id"],
        cycle_id=evaluation.cycle_id,
        plan_id=evaluation.plan_id,
        attempt_id=evaluation.attempt_id,
        request_id=evaluation.request_id,
        authorization_id=evaluation.authorization_id,
        evidence_digest=evaluation.evidence_digest,
        operator_disposition="accept_evidence_for_future_application_consideration",
        operator_issued=True,
        issued_sequence=5050,
        accepted_evidence=True,
    )
    artifact = gsr.build_application_artifact_from_review_item(item, evaluation, disposition_record)
    request = gsr.make_application_request(evaluation, disposition_record, artifact, requested_sequence=5051)
    authorization = gsr.make_application_authorization(request, issued_sequence=5052, expiration_sequence=5060)
    eligibility = gsr.evaluate_application_eligibility(evaluation, disposition_record, artifact, request, authorization, sequence=5053)
    new_text = "def analyze(text):\n    return {'assertion': text, 'evidence_required': True}\n"
    post_hash = hashlib.sha256(new_text.encode("utf-8")).hexdigest()
    operation = gsr.ApplicationPlanOperation(
        sequence=1,
        operation="apply_exact_reviewed_text_change",
        target_path="fixture_language_capability.py",
        expected_current_hash=pre_hash,
        expected_post_application_hash=post_hash,
        rollback_operation="restore_exact_content",
        rollback_artifact_id="rollback-e2e",
        rollback_target_path="fixture_language_capability.py",
        rollback_expected_hash=pre_hash,
    )
    plan = gsr.make_application_plan(
        eligibility,
        ordered_target_operations=(operation,),
        expected_post_application_hashes={"fixture_language_capability.py": post_hash},
        rollback_metadata=(
            {
                "target_path": "fixture_language_capability.py",
                "rollback_operation": "restore_exact_content",
                "rollback_target_path": "fixture_language_capability.py",
                "rollback_artifact_id": "rollback-e2e",
                "rollback_expected_hash": pre_hash,
            },
        ),
        required_validation_commands=("fixture-focused", "fixture-adjacent"),
        application_sequence=5054,
    )
    preflight = gsr.evaluate_application_preflight(eligibility, plan, root=tmp_path, sequence=5055)
    application = gsr.execute_governed_application_attempt(
        preflight,
        plan,
        root=tmp_path,
        reviewed_text_by_target={"fixture_language_capability.py": new_text},
        validation_results={"fixture-focused": True, "fixture-adjacent": True},
        sequence=5056,
    )
    validation = gsr.classify_post_application_validation(application, focused_tests_passed=True, adjacent_regressions_passed=True, startup_smoke_passed=True)
    promotion_request = gsr.make_capability_promotion_request(
        capability_id=spec.specification.capability_id,
        proposal_id=item.proposal_id,
        application_attempt_id=application.evidence.application_attempt_id,
        validation_id=validation.validation_id,
        requested_evidence_tier="available",
        sequence=5057,
    )
    promotion_authorization = gsr.make_capability_promotion_authorization(promotion_request, issued_sequence=5058)
    promoted = gsr.promote_validated_capability_evidence(promotion_request, promotion_authorization, validation, sequence=5059)
    runtime_state = gsr.OARRuntimeState(runtime_state_id="runtime-e2e", available_capability_ids=(promoted.capability_id,))
    recovered = gsr.recover_oar_runtime_after_restart(gsr.shutdown_oar_runtime_cleanly(runtime_state, checkpoint_id="checkpoint-e2e"), integrity_valid=True)
    activated, reason, live_state = gsr.activate_oar_live_runtime(recovered, capability_ids=(promoted.capability_id,))

    assert application.accepted and application.application_performed
    assert validation.classification == "application_validated"
    assert promoted.available is True and promoted.active is False
    assert activated is True and reason == "live_runtime_started_with_explicit_activation"
    assert live_state.active_capability_ids == (promoted.capability_id,)
    assert threading.active_count() == thread_count_before
    assert tuple(multiprocessing.active_children()) == child_processes_before


def test_e2e_1_denials_cover_substitution_absent_queue_decline_replay_and_activation(tmp_path: Path):
    compiled, _approval, _mission, graph, self_model, analysis, selection, spec, options, architecture, *_rest = _mission_to_cde_chain()
    assert gsr.select_capability_prerequisite(analysis, graph.graph).selected_capability_id == selection.selected_capability_id

    bad_request = replace(compiled.request, original_operator_mission="different mission")
    bad_compile = gsr.compile_language_development_mission(bad_request, compiled.original_authorization, sequence=5002)
    assert bad_compile.accepted is False

    item, _pre_hash = _review_item(tmp_path, compiled, spec, options, architecture)
    decline_request = gsr.make_operator_proposal_disposition_request(item, requested_disposition="declined", reason_code="insufficient_evidence", operator_comment="decline", ui_action_id="ui-decline", sequence=6100)
    decline_auth = gsr.make_operator_proposal_disposition_authorization(decline_request, operator_identity="operator", issued_sequence=6101)
    declined = gsr.apply_operator_proposal_disposition(item, decline_request, decline_auth, sequence=6102)
    assert declined.accepted and declined.disposition.operator_disposition == "declined"
    duplicate = gsr.apply_operator_proposal_disposition(item, decline_request, decline_auth, (declined.disposition,), sequence=6103)
    assert duplicate.accepted is False
    assert duplicate.reason == "duplicate_terminal_disposition"

    state = gsr.OARRuntimeState(runtime_state_id="runtime-denial", available_capability_ids=("approved-capability",), rollback_required_ids=("failed-app",))
    ok, reason, _ = gsr.activate_oar_live_runtime(state, capability_ids=("approved-capability",))
    assert ok is False
    assert reason == "rollback_required"


def test_e2e_1_durability_logs_journal_recovery_and_startup_paused(tmp_path: Path):
    store = DurableRuntimeStateStore(tmp_path / "runtime-state", runtime_session_id="session-e2e")
    start = store.append_event("runtime_started", phase="e2e", lifecycle_before="stopped", lifecycle_after="development_runtime")
    store.write_checkpoint("checkpoint-e2e", default_clean_checkpoint_state(mission_id="mission-e2e"))
    store.write_intent("application-action", "reviewed_patch_application", authorization_id="app-auth")
    recovery = DurableRuntimeStateStore(tmp_path / "runtime-state", runtime_session_id="session-e2e").recover_startup()
    status = DurableRuntimeStateStore(tmp_path / "runtime-state", runtime_session_id="session-e2e").runtime_status_snapshot()

    assert start["monotonic_sequence"] == 1
    assert recovery.operator_review_required is True
    assert recovery.incomplete_action_ids == ("application-action",)
    assert recovery.development_runtime_started is False
    assert recovery.live_runtime_started is False
    assert status.active_runtime_mode == "stopped"
