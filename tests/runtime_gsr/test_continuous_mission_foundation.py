from dataclasses import replace

import pytest

from orchestration.runtime.continuous_mission_foundation import (
    BehavioralEvaluationRecord,
    OBSERVATION_STATE,
    MainGoalContract,
    assess_main_goal_completion,
    behavioral_failure_to_runtime_finding,
    capability_is_acquired,
    capability_inventory_from_knowledge,
    compile_behavioral_failure_record,
    compile_developmental_insight_requests,
    compile_developmental_operator_explanation,
    compile_initial_main_goal,
    compile_long_horizon_objective,
    derive_developmental_capability_plan,
    derive_developmental_next_goal_candidates,
    derive_next_main_goal,
    derive_subgoal_evidence_for_main_goal,
    assess_developmental_capability_state,
    dirty_worktree_policy,
    main_goal_from_developmental_plan,
    evidence_to_findings,
    make_satisfied_transfer_record,
    normalize_capability_record_for_recovery,
    promote_capability_with_behavioral_evaluation,
    rank_weakness_frontier,
    validate_behavioral_evaluation,
)
from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_runtime,
    attach_continuous_mission,
    consume_continuous_capability_reassessment,
    consume_continuous_mission_application_decision,
    consume_continuous_operator_interaction_response,
    continue_continuous_mission_after_reassessment,
    controller_snapshot,
    derive_observation_exit_actions,
    export_continuous_mission_restart_state,
    exit_observation_with_action_derivation,
    mark_continuous_api_unavailable,
    pause_continuous_mission_for_application,
    queue_continuous_mission_sandbox_work,
    refresh_continuous_mission_frontier,
    recover_accepted_boundary_operator_requests,
    recover_missing_continuous_application_review_request,
    restore_continuous_mission_restart_state,
    assess_and_advance_continuous_main_goal,
    refresh_developmental_self_direction,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import execute_continuous_active_subgoal


def _evidence():
    return (
        {
            "evidence_source": "quote metric",
            "observed_behavior": "quoted imperative text is not isolated from evidence",
            "first_incorrect_transition": "quoted text -> instruction authority leaks into evidence handling",
            "affected_capability": "quote_instruction_isolation",
            "baseline_metric": "quote_instruction_isolation=0.0",
            "confidence": 0.8,
            "operator_value": 0.9,
            "severity": 0.7,
            "estimated_implementation_breadth": "small",
            "validation_method": "focused_quote_tests",
        },
        {
            "evidence_source": "speculative note",
            "observed_behavior": "maybe improve aesthetics",
            "affected_capability": "cosmetic_ui",
        },
    )


def _controller_with_subgoal():
    controller = start_continuous_runtime_controller(session_id="continuous-foundation")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(controller, _evidence())
    controller = refresh_continuous_mission_frontier(controller)
    return select_continuous_mission_subgoal(controller)


def _behavioral_failure_evidence(**overrides):
    evidence = {
        "source_type": "runtime_transition_violation",
        "source_reference": "tests/runtime_gsr/test_controller_transition.py::test_restart_resumes",
        "source_digest": "source-digest-a",
        "observed_behavior": "restart recovery raises before capability reassessment",
        "expected_behavior": "restart recovery restores the active subgoal and then reassesses capability state",
        "expected_behavior_identity": "restart_restores_active_subgoal_before_reassessment",
        "expected_behavior_authority": "state_machine_transition_contract",
        "expected_vs_observed_result": "exception_before_reassessment",
        "baseline_reproduction": "pytest tests/runtime_gsr/test_controller_transition.py::test_restart_resumes",
        "reproduction_command_or_predicate": "pytest tests/runtime_gsr/test_controller_transition.py::test_restart_resumes",
        "reproduction_attempts": (
            {
                "command_or_predicate_identity": "pytest restart-resumes",
                "input_or_state_reference": "restart_state_fixture_a",
                "status": "completed",
                "result_classification": "reproduced",
                "result_digest": "result-digest-a",
                "environment_digest": "env-digest-a",
                "safety_boundary": "local_deterministic_no_mutation",
                "authoritative_runner_identity": "pytest",
            },
        ),
        "reproduction_result": "reproduced",
        "reproduction_output_digest": "output-digest-a",
        "first_incorrect_transition": "restart_state_loaded -> capability reassessment",
        "affected_runtime_stage": "restart_recovery",
        "affected_capability_id": "restart_reassessment_bridge",
        "originating_mission_id": "continuous-mission-test",
        "suspected_owner_paths": ("orchestration/runtime/continuous_runtime_controller.py",),
        "independent_evidence_paths": ("tests/runtime_gsr/test_controller_transition.py",),
        "allowed_scope": ("orchestration/runtime", "tests/runtime_gsr"),
        "excluded_scope": ("DELTA-75", "reports/RC4_*"),
        "materiality_reason": "restart cannot continue developmental work after worker recovery",
        "reproducibility_status": "reproduced",
        "occurrence_count": 1,
        "first_seen": "2026-07-16T00:00:00+00:00",
        "last_seen": "2026-07-16T00:00:00+00:00",
        "environment_digest": "env-digest-a",
        "state_digest": "state-digest-a",
        "authority_class": "local_execution_allowed",
        "ambiguity_status": "resolved",
        "current_disposition": "observed",
    }
    evidence.update(overrides)
    return evidence


def test_contract_helpers_are_not_a_second_controller():
    import orchestration.runtime.continuous_mission_foundation as foundation

    assert not hasattr(foundation, "ContinuousMissionState")
    assert not hasattr(foundation, "run_operator_language_foundation_pilot")
    assert not hasattr(foundation, "write_continuous_mission_checkpoint")
    assert not hasattr(foundation, "pause_for_application")


def test_broad_mission_compilation_is_owned_by_existing_controller():
    controller = start_continuous_runtime_controller(session_id="continuous-compile")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    snapshot = controller_snapshot(controller)

    assert controller.continuous_mission_state == "mission_accepted"
    assert controller.continuous_mission_contract["normalized_goal"] == "optimize_delta_runtime_continuously"
    assert controller.continuous_mission_contract["local_authority"]["continuous_local_authority"] is True
    assert controller.continuous_mission_contract["local_authority"]["artificial_attempt_ceiling"] is False
    assert controller.continuous_mission_contract["api_authority"]["enabled"] is False
    assert snapshot["continuous_mission"]["state"] == "mission_accepted"
    assert controller.active_objective is not None
    assert controller.active_objective.source == "CONTINUOUS_MISSION"


def test_assessment_intake_accepts_evidence_and_marks_speculation_diagnostic_only():
    findings = evidence_to_findings(_evidence())

    assert len(findings) == 2
    assert findings[0].diagnostic_only is False
    assert findings[1].diagnostic_only is True


def test_frontier_ranking_is_deterministic_and_excludes_solved_or_duplicate_weaknesses():
    findings = evidence_to_findings(
        _evidence()
        + (
            {
                "evidence_source": "transfer status",
                "observed_behavior": "transfer dependency identity already satisfied",
                "first_incorrect_transition": "solved weakness should not re-enter frontier",
                "affected_capability": "transfer_dependency_identity_preservation",
                "baseline_metric": "transfer_dependency_identity_preservation=1.0",
                "confidence": 0.95,
                "operator_value": 0.7,
                "severity": 0.2,
                "validation_method": "knowledge_retention",
            },
        )
    )
    first = rank_weakness_frontier(findings, knowledge_ledger=(make_satisfied_transfer_record(),))
    second = rank_weakness_frontier(findings, knowledge_ledger=(make_satisfied_transfer_record(),))

    assert [item.semantic_signature for item in first] == [item.semantic_signature for item in second]
    assert first[0].status == "eligible"
    solved = [item for item in first if item.description.startswith("transfer dependency")]
    assert solved and solved[0].status == "satisfied"


def test_legacy_satisfied_record_without_behavioral_evaluation_is_downgraded_and_reopens_gap():
    legacy = replace(
        make_satisfied_transfer_record(),
        reassessment="satisfied",
        evidence_stage="legacy_unclassified",
        capability_acquired=False,
        behavioral_evaluation_ref="",
        behavioral_evaluation=None,
    )
    recovered = normalize_capability_record_for_recovery(legacy)

    assert recovered.reassessment == "candidate_structurally_validated"
    assert recovered.evidence_stage == "candidate_structurally_validated"
    assert recovered.capability_acquired is False
    assert recovered.eligible_for_behavioral_evaluation is True
    assert capability_is_acquired(recovered) is False

    findings = evidence_to_findings(
        (
            {
                "evidence_source": "legacy transfer record",
                "observed_behavior": "transfer dependency identity remains unproven by independent behavior",
                "first_incorrect_transition": "candidate artifact -> legacy satisfied record -> solved frontier",
                "affected_capability": "transfer_dependency_identity_preservation",
                "baseline_metric": "transfer_dependency_identity_preservation=0.0",
                "confidence": 0.8,
                "operator_value": 0.9,
                "severity": 0.8,
                "validation_method": "legacy_recovery",
            },
        )
    )
    ranked = rank_weakness_frontier(findings, knowledge_ledger=(recovered,))
    assert ranked[0].status == "eligible"


def test_behavioral_evaluation_is_required_for_capability_promotion():
    structural = replace(
        make_satisfied_transfer_record(),
        reassessment="candidate_structurally_validated",
        evidence_stage="candidate_structurally_validated",
        capability_acquired=False,
        eligible_for_behavioral_evaluation=True,
        behavioral_evaluation_ref="",
        behavioral_evaluation=None,
    )
    failed = BehavioralEvaluationRecord(
        evaluation_id="eval-failed",
        task_family_id="transfer_dependency_identity_preservation",
        capability_id="transfer_dependency_identity_preservation",
        developmental_gap_id="transfer-gap",
        baseline_attempt_id="baseline-1",
        candidate_id="candidate-1",
        evaluation_protocol_version="v1",
        task_source="candidate_generated",
        training_case_ids=("case-1",),
        sealed_or_preexisting_case_ids=(),
        control_case_ids=("control-1",),
        baseline_metrics={"target": 0.0},
        post_candidate_metrics={"target": 1.0},
        transfer_metrics={"target": 1.0, "threshold": 1.0},
        regression_metrics={"controls_stable": True},
        evidence_independence={
            "case_source": "candidate_generated",
            "candidate_generated_expected_outputs": True,
            "self_reported_success": True,
            "artifact_existence_only": True,
        },
        disposition="behaviorally_demonstrated",
        evidence_refs=("candidate_metric",),
    )
    valid, failures = validate_behavioral_evaluation(failed)
    promoted = promote_capability_with_behavioral_evaluation(structural, failed)

    assert valid is False
    assert "missing_sealed_or_preexisting_cases" in failures
    assert capability_is_acquired(promoted) is False
    assert promoted.reassessment == "insufficient_independent_evidence"

    passing = BehavioralEvaluationRecord(
        evaluation_id="eval-passing",
        task_family_id="transfer_dependency_identity_preservation",
        capability_id="transfer_dependency_identity_preservation",
        developmental_gap_id="transfer-gap",
        baseline_attempt_id="baseline-1",
        candidate_id="candidate-1",
        evaluation_protocol_version="v1",
        task_source="immutable_benchmark_fixture",
        training_case_ids=("train-1",),
        sealed_or_preexisting_case_ids=("sealed-1", "sealed-2"),
        control_case_ids=("control-1",),
        baseline_metrics={"target": 0.0},
        post_candidate_metrics={"target": 1.0},
        transfer_metrics={"target": 1.0, "threshold": 1.0},
        regression_metrics={"controls_stable": True},
        evidence_independence={
            "case_source": "sealed",
            "candidate_generated_expected_outputs": False,
            "self_reported_success": False,
            "artifact_existence_only": False,
        },
        disposition="behaviorally_demonstrated",
        evidence_refs=("sealed-result", "control-result"),
    )
    valid, failures = validate_behavioral_evaluation(passing)
    demonstrated = promote_capability_with_behavioral_evaluation(structural, passing)

    assert valid is True
    assert failures == ()
    assert demonstrated.evidence_stage == "behaviorally_demonstrated"
    assert demonstrated.capability_acquired is True
    assert capability_is_acquired(demonstrated) is True


def test_subgoal_compilation_selects_one_measurable_active_goal_through_controller():
    controller = _controller_with_subgoal()

    assert controller.continuous_mission_state == "subgoal_active"
    assert controller.continuous_active_subgoal["measurable_objective"]
    assert controller.continuous_active_subgoal["rollback_condition"]
    assert controller.active_objective is not None
    assert controller.active_objective.source == "CONTINUOUS_SUBGOAL"


def test_sandbox_queue_and_application_boundary_are_controller_owned():
    controller = queue_continuous_mission_sandbox_work(_controller_with_subgoal())
    paused = pause_continuous_mission_for_application(controller, candidate_id="candidate-1", decision_id="decision-1")

    assert paused.continuous_mission_state == "awaiting_operator_application"
    assert paused.pending_application_decision_id == "decision-1"
    assert paused.active_work_item == "awaiting_operator_application"
    resumed = consume_continuous_mission_application_decision(paused, decision_id="decision-1", action="APPLY_VALIDATED_CANDIDATE")
    assert resumed.pending_application_decision_id == ""
    assert resumed.continuous_mission_state == "post_application_validation"
    with pytest.raises(ValueError):
        consume_continuous_mission_application_decision(resumed, decision_id="decision-1", action="REJECT_CANDIDATE")


def test_capability_reassessment_consumes_active_signature_and_continues_without_new_prompt():
    controller = _controller_with_subgoal()
    record = replace(
        make_satisfied_transfer_record(),
        capability_id="quote_instruction_isolation",
        original_weakness="quoted instruction isolation",
        first_incorrect_transition="quote -> authority leak",
        exact_candidate="orchestration/runtime/live45_quote_instruction_isolation.py",
        tests_added=("tests/runtime_gsr/test_live45_quote_instruction_isolation.py",),
        held_out_evidence={"sealed": False, "result": 1.0},
        reassessment="satisfied",
        residual_uncertainty="held-out case disclosed before validation",
    )
    reassessed = consume_continuous_capability_reassessment(controller, record)
    continued = continue_continuous_mission_after_reassessment(reassessed)

    assert reassessed.continuous_consumed_weakness_signatures
    assert reassessed.continuous_active_subgoal == {}
    assert continued.continuous_mission_state == "subgoal_active"
    assert continued.continuous_active_subgoal


def test_structural_candidate_is_queued_for_behavioral_evaluation_before_frontier_or_operator_selection():
    controller = _controller_with_subgoal()
    structural = replace(
        make_satisfied_transfer_record(),
        capability_id="quote_instruction_isolation",
        reassessment="candidate_structurally_validated",
        evidence_stage="candidate_structurally_validated",
        capability_acquired=False,
        eligible_for_behavioral_evaluation=True,
        behavioral_evaluation_ref="",
        behavioral_evaluation=None,
        metrics_before_after={"baseline": "quote_instruction_isolation=0.0", "candidate_id": "candidate-structural"},
    )

    queued = continue_continuous_mission_after_reassessment(
        consume_continuous_capability_reassessment(controller, structural)
    )
    restart_state = export_continuous_mission_restart_state(queued)
    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id=queued.session_id),
        restart_state,
    )

    assert queued.continuous_mission_state == "behavioral_evaluation_active"
    assert queued.continuous_active_subgoal["execution_kind"] == "independent_behavioral_evaluation"
    assert queued.continuous_active_subgoal["behavioral_evaluation"]["capability_id"] == "quote_instruction_isolation"
    assert queued.continuous_mission_state != "awaiting_operator_insight"
    assert restored.continuous_active_subgoal == queued.continuous_active_subgoal
    assert restored.continuous_mission_state == "behavioral_evaluation_active"


def test_api_exhaustion_preserves_provider_task_and_does_not_complete_mission():
    controller = _controller_with_subgoal()
    blocked = mark_continuous_api_unavailable(controller, pending_task="provider-critique-1", reason="quota_exhausted")

    assert "provider-critique-1" in blocked.continuous_api_authority["pending_provider_tasks"]
    assert blocked.continuous_api_authority["unavailability_reason"] == "quota_exhausted"
    assert blocked.continuous_mission_state not in {"mission_complete", "goal_exhausted", "runtime_optimized"}


def test_restart_serialization_restores_continuous_mission_fields_once():
    controller = pause_continuous_mission_for_application(
        queue_continuous_mission_sandbox_work(_controller_with_subgoal()),
        candidate_id="candidate-1",
        decision_id="decision-1",
    )
    blocked = mark_continuous_api_unavailable(controller, pending_task="provider-critique-1", reason="quota_exhausted")
    restart_state = export_continuous_mission_restart_state(blocked)
    fresh = start_continuous_runtime_controller(session_id=blocked.session_id)
    restored = restore_continuous_mission_restart_state(fresh, restart_state)

    assert restored.continuous_mission_state == blocked.continuous_mission_state
    assert restored.continuous_mission_contract == blocked.continuous_mission_contract
    assert restored.continuous_mission_frontier == blocked.continuous_mission_frontier
    assert restored.continuous_active_subgoal == blocked.continuous_active_subgoal
    assert restored.pending_application_decision_id == "decision-1"
    assert restored.continuous_api_authority["pending_provider_tasks"] == ("provider-critique-1",)
    with pytest.raises(ValueError):
        restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="other"), restart_state)


def test_empty_frontier_enters_observation_and_later_evidence_reactivates():
    controller = start_continuous_runtime_controller(session_id="continuous-observe")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_runtime(controller, ())
    controller = refresh_continuous_mission_frontier(controller)
    observed = select_continuous_mission_subgoal(controller)

    assert observed.continuous_mission_state == "subgoal_active"
    assert observed.continuous_active_subgoal
    reactivated = select_continuous_mission_subgoal(
        refresh_continuous_mission_frontier(assess_continuous_mission_runtime(observed, _evidence()))
    )
    assert reactivated.continuous_active_subgoal


def test_empty_frontier_runs_main_goal_assessment_not_completion_claim():
    controller = start_continuous_runtime_controller(session_id="main-goal-empty-frontier")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    advanced = assess_and_advance_continuous_main_goal(controller)

    assert advanced.continuous_mission_state == "subgoal_active"
    assert advanced.continuous_active_subgoal["measurable_objective"]
    assert advanced.continuous_main_goal["disposition"] == "partially_satisfied"
    assert advanced.continuous_completed_main_goals == ()


def test_main_goal_has_no_fixed_subgoal_count_policy():
    controller = start_continuous_runtime_controller(session_id="main-goal-variable-count")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    contract = compile_initial_main_goal(type("Contract", (), controller.continuous_mission_contract))
    two_goal = MainGoalContract(**{**contract.as_dict(), "success_criteria": ("a", "b"), "prerequisite_graph": {"a": (), "b": ()}})
    fifteen = tuple(f"c{index}" for index in range(15))
    fifteen_goal = MainGoalContract(**{**contract.as_dict(), "success_criteria": fifteen, "prerequisite_graph": {item: () for item in fifteen}})

    assert len(derive_subgoal_evidence_for_main_goal(two_goal, (), max_items=20)) == 2
    assert len(derive_subgoal_evidence_for_main_goal(fifteen_goal, (), max_items=20)) == 15


def test_satisfied_main_goal_derives_next_main_goal_from_capability_inventory():
    controller = start_continuous_runtime_controller(session_id="main-goal-satisfied")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    current = MainGoalContract(**controller.continuous_main_goal)
    records = tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in current.success_criteria
    )
    assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
    next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)

    assert assessed.disposition == "satisfied"
    assert next_goal.normalized_objective == "autonomous_evidence_discovery"
    assert next_goal.main_goal_id != assessed.main_goal_id


def test_no_generic_next_main_goal_is_fabricated_for_runtime_mission():
    controller = start_continuous_runtime_controller(session_id="main-goal-no-generic-loop")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    first = MainGoalContract(**controller.continuous_main_goal)
    second = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), first, ())
    assert second is not None
    completed_second = MainGoalContract(**{**second.as_dict(), "disposition": "satisfied"})

    assert derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), completed_second, ()) is None


def test_completed_developmental_self_direction_evidence_derives_resource_insight_goal():
    controller = start_continuous_runtime_controller(session_id="self-direction-followup")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    first = MainGoalContract(**controller.continuous_main_goal)
    records = tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in first.success_criteria
    )
    assessed = assess_main_goal_completion(first, records, eligible_frontier_exists=False)
    second = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
    assert second is not None
    completed_second = MainGoalContract(**{**second.as_dict(), "disposition": "satisfied"})
    records += tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in second.success_criteria
    )
    third = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), completed_second, records)

    assert second.normalized_objective == "developmental_self_direction_evidence"
    assert third is not None
    assert third.normalized_objective == "resource_backed_developmental_insight"
    first_resource_subgoal = derive_subgoal_evidence_for_main_goal(third, records, max_items=1)
    assert first_resource_subgoal[0]["affected_capability"] == "uncertainty_detection_for_goal_selection"


def test_articulate_development_goal_derives_grounded_communication_after_resource_insight():
    controller = start_continuous_runtime_controller(session_id="articulate-followup")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    first = MainGoalContract(**controller.continuous_main_goal)
    first_records = tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in first.success_criteria
    )
    second = derive_next_main_goal(
        type("Contract", (), controller.continuous_mission_contract),
        assess_main_goal_completion(first, first_records, eligible_frontier_exists=False),
        first_records,
    )
    second_records = first_records + tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in second.success_criteria
    )
    third = derive_next_main_goal(
        type("Contract", (), controller.continuous_mission_contract),
        MainGoalContract(**{**second.as_dict(), "disposition": "satisfied"}),
        second_records,
    )
    third_records = second_records + tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in third.success_criteria
    )
    fourth = derive_next_main_goal(
        type("Contract", (), controller.continuous_mission_contract),
        MainGoalContract(**{**third.as_dict(), "disposition": "satisfied"}),
        third_records,
    )

    assert third.normalized_objective == "resource_backed_developmental_insight"
    assert fourth is not None
    assert fourth.normalized_objective == "grounded_operator_communication"
    communication_subgoal = derive_subgoal_evidence_for_main_goal(fourth, third_records, max_items=1)
    assert communication_subgoal[0]["affected_capability"] == "state_grounded_progress_summary"


def test_grounded_communication_derives_meaningful_progress_stall_detection():
    controller = start_continuous_runtime_controller(session_id="meaningful-progress-followup")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    first = MainGoalContract(**controller.continuous_main_goal)
    records = ()
    current = first
    for expected in (
        "developmental_self_assessment",
        "developmental_self_direction_evidence",
        "resource_backed_developmental_insight",
        "grounded_operator_communication",
    ):
        assert current.normalized_objective == expected
        goal_records = tuple(
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed",
                    "successful_mechanism": criterion,
                    "reassessment": "satisfied",
                }
            )
            for criterion in current.success_criteria
        )
        records += goal_records
        assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
        next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
        if expected != "grounded_operator_communication":
            assert next_goal is not None
            current = next_goal

    assert next_goal is not None
    assert next_goal.normalized_objective == "meaningful_progress_stall_detection"
    evidence = derive_subgoal_evidence_for_main_goal(next_goal, records, max_items=1)
    assert evidence[0]["affected_capability"] == "meaningful_transition_tracking"


def test_meaningful_progress_derives_autonomous_evidence_acquisition():
    controller = start_continuous_runtime_controller(session_id="autonomous-evidence-followup")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    current = MainGoalContract(**controller.continuous_main_goal)
    records = ()
    for expected in (
        "developmental_self_assessment",
        "developmental_self_direction_evidence",
        "resource_backed_developmental_insight",
        "grounded_operator_communication",
        "meaningful_progress_stall_detection",
    ):
        assert current.normalized_objective == expected
        goal_records = tuple(
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed",
                    "successful_mechanism": criterion,
                    "reassessment": "satisfied",
                }
            )
            for criterion in current.success_criteria
        )
        records += goal_records
        assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
        next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
        if expected != "meaningful_progress_stall_detection":
            assert next_goal is not None
            current = next_goal

    assert next_goal is not None
    assert next_goal.normalized_objective == "autonomous_evidence_acquisition"
    assert next_goal.next_main_goal_candidates[0] == "autonomous_evidence_acquisition"
    assert "operator_goal_reinterpretation_check" in next_goal.next_main_goal_candidates
    assert "idle_resource_efficiency" in next_goal.next_main_goal_candidates
    assert "selected from ranked developmental next-goal candidates" in next_goal.completion_rationale
    assert "resource_need=local_artifact_mining_first" in next_goal.completion_rationale
    partially_satisfied_next_goal = assess_main_goal_completion(next_goal, records, eligible_frontier_exists=False)
    assert "prior_rationale_id=" in partially_satisfied_next_goal.completion_rationale
    assert "prior_rationale_summary=selected from ranked developmental next-goal candidates" in partially_satisfied_next_goal.completion_rationale
    completion_records = records + tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in next_goal.success_criteria
    )
    completed_next_goal = assess_main_goal_completion(partially_satisfied_next_goal, completion_records, eligible_frontier_exists=False)
    assert "prior_rationale_id=" in completed_next_goal.completion_rationale
    assert "prior_rationale_summary=selected from ranked developmental next-goal candidates" in completed_next_goal.completion_rationale
    evidence = derive_subgoal_evidence_for_main_goal(next_goal, records, max_items=1)
    assert evidence[0]["affected_capability"] == "frontier_uncertainty_scan"


def test_meaningful_progress_next_goal_candidates_are_ranked_from_evidence():
    controller = start_continuous_runtime_controller(session_id="ranked-next-goal-candidates")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    current = MainGoalContract(**controller.continuous_main_goal)
    records = ()
    for _ in range(4):
        records += tuple(
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed",
                    "successful_mechanism": criterion,
                    "reassessment": "satisfied",
                }
            )
            for criterion in current.success_criteria
        )
        assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
        next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
        if next_goal is None:
            break
        current = next_goal

    assert current.normalized_objective == "meaningful_progress_stall_detection"
    records += tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in current.success_criteria
    )
    assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
    candidates = derive_developmental_next_goal_candidates(type("Contract", (), controller.continuous_mission_contract), assessed, records)
    assert tuple(candidate.normalized_objective for candidate in candidates) == (
        "autonomous_evidence_acquisition",
        "operator_goal_reinterpretation_check",
        "idle_resource_efficiency",
    )
    assert candidates[0].score > candidates[1].score > candidates[2].score
    assert candidates[0].evidence_basis == current.success_criteria
    assert candidates[0].resource_need == "local_artifact_mining_first"


def test_repeated_observation_does_not_nest_rationale_text():
    controller = start_continuous_runtime_controller(session_id="bounded-rationale")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    current = MainGoalContract(**controller.continuous_main_goal)
    records = ()
    for _ in range(5):
        records += tuple(
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed",
                    "successful_mechanism": criterion,
                    "reassessment": "satisfied",
                }
            )
            for criterion in current.success_criteria
        )
        assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
        next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
        if next_goal is not None:
            current = next_goal

    assert current.normalized_objective == "autonomous_evidence_acquisition"
    once = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
    twice = assess_main_goal_completion(once, records, eligible_frontier_exists=False)
    assert once.completion_rationale == twice.completion_rationale
    assert once.completion_rationale.count("selected from ranked developmental next-goal candidates") == 1
    assert "prior_active_rationale" not in once.completion_rationale


def test_legacy_nested_rationale_is_normalized_without_losing_selection_provenance():
    controller = start_continuous_runtime_controller(session_id="legacy-rationale-normalization")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    goal = MainGoalContract(
        **{
            **MainGoalContract(**controller.continuous_main_goal).as_dict(),
            "normalized_objective": "autonomous_evidence_acquisition",
            "success_criteria": ("frontier_uncertainty_scan",),
            "next_main_goal_candidates": ("autonomous_evidence_acquisition", "operator_goal_reinterpretation_check"),
            "completion_rationale": (
                "all required criteria have satisfied evidence; prior_active_rationale=empty frontier is not completion; "
                "prior_active_rationale=selected from ranked developmental next-goal candidates after legacy; ranking=x; selected_rationale=y"
            ),
        }
    )
    records = (
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": "frontier_uncertainty_scan",
                "original_weakness": "frontier scan completed",
                "successful_mechanism": "frontier scan",
                "reassessment": "satisfied",
            }
        ),
    )
    assessed = assess_main_goal_completion(goal, records, eligible_frontier_exists=False)
    assert "prior_active_rationale" not in assessed.completion_rationale
    assert assessed.completion_rationale.count("selected from ranked developmental next-goal candidates") == 1
    assert "prior_rationale_id=" in assessed.completion_rationale


def test_autonomous_evidence_acquisition_derives_next_goal_from_candidate_comparison():
    controller = start_continuous_runtime_controller(session_id="post-evidence-next-goal")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    current = MainGoalContract(**controller.continuous_main_goal)
    records = ()
    for _ in range(6):
        records += tuple(
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed",
                    "successful_mechanism": criterion,
                    "reassessment": "satisfied",
                }
            )
            for criterion in current.success_criteria
        )
        assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
        next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
        if next_goal is None:
            break
        current = next_goal

    assert current.normalized_objective == "capability_transfer_validation"
    assert current.next_main_goal_candidates == (
        "capability_transfer_validation",
        "evidence_source_diversity",
        "developmental_communication_calibration",
    )
    assert "selected from ranked developmental next-goal candidates" in current.completion_rationale
    assert "local_held_out_and_transfer_artifact_mining" in current.completion_rationale
    evidence = derive_subgoal_evidence_for_main_goal(current, records, max_items=1)
    assert evidence[0]["affected_capability"] == "cross_context_transfer_case_generation"


def test_completed_transfer_validation_derives_next_goal_from_remaining_candidates():
    controller = start_continuous_runtime_controller(session_id="post-transfer-next-goal")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    current = MainGoalContract(**controller.continuous_main_goal)
    records = ()
    for _ in range(7):
        records += tuple(
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed",
                    "successful_mechanism": criterion,
                    "reassessment": "satisfied",
                }
            )
            for criterion in current.success_criteria
        )
        assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
        next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
        if next_goal is None:
            break
        current = next_goal

    assert current.normalized_objective == "evidence_source_diversity"
    assert current.next_main_goal_candidates == (
        "evidence_source_diversity",
        "developmental_communication_calibration",
    )
    assert "capability_transfer_validation" not in current.next_main_goal_candidates
    assert "selected from ranked developmental next-goal candidates" in current.completion_rationale
    assert "source diversity remains less urgent than transfer validation" in current.completion_rationale
    evidence = derive_subgoal_evidence_for_main_goal(current, records, max_items=1)
    assert evidence[0]["affected_capability"] == "source_diversity_inventory"


def test_local_only_limitations_produce_developmental_gaps_and_lower_confidence():
    objective = compile_long_horizon_objective("Develop yourself into an increasingly capable, articulate, self-directed system.")
    local_only = make_satisfied_transfer_record().__class__(
        **{
            **make_satisfied_transfer_record().as_dict(),
            "capability_id": "local_fixture_skill",
            "original_weakness": "local fixture passed but broad use unproven",
            "successful_mechanism": "local sandbox diagnostic candidate",
            "application_evidence": "tracked application not performed",
            "held_out_evidence": {"sealed": False, "result": 1.0},
            "regression_evidence": "focused continuous subgoal executor tests",
            "reproduction_evidence": "local clean reproduction only",
            "residual_uncertainty": "candidate is local diagnostic unless application review is separately requested",
            "reassessment": "satisfied",
        }
    )
    inventory = capability_inventory_from_knowledge((local_only,))
    assessment = assess_developmental_capability_state(objective, inventory)

    assert "local_fixture_skill" in assessment.verified_capabilities
    assert "local_diagnostic_only_validation" in assessment.developmental_gaps
    assert "missing_tracked_application_proof" in assessment.developmental_gaps
    assert "fixture_scoped_validation" in assessment.developmental_gaps
    assert assessment.confidence < 0.8
    assert assessment.needs_additional_insight is True
    assert assessment.missing_confidence_questions


def test_controller_refreshes_limitation_gaps_before_observation_or_advance():
    controller = start_continuous_runtime_controller(session_id="controller-refreshes-limitation-gaps")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    local_only = make_satisfied_transfer_record().__class__(
        **{
            **make_satisfied_transfer_record().as_dict(),
            "capability_id": "local_fixture_skill",
            "original_weakness": "local fixture passed but broad use unproven",
            "successful_mechanism": "local sandbox diagnostic candidate",
            "application_evidence": "tracked application not performed",
            "held_out_evidence": {"sealed": False, "result": 1.0},
            "regression_evidence": "focused continuous subgoal executor tests",
            "reproduction_evidence": "local clean reproduction only",
            "residual_uncertainty": "candidate is local diagnostic unless application review is separately requested",
            "reassessment": "satisfied",
        }
    )
    updated = assess_and_advance_continuous_main_goal(replace(controller, continuous_knowledge_ledger=(local_only.as_dict(),)))
    snapshot = controller_snapshot(updated)["continuous_mission"]

    assert "local_diagnostic_only_validation" in snapshot["developmental_self_assessment"]["developmental_gaps"]
    assert snapshot["developmental_self_assessment"]["needs_additional_insight"] is True


def test_empty_gap_requires_limitations_to_be_resolved_or_absent():
    objective = compile_long_horizon_objective("Develop yourself into an increasingly capable, articulate, self-directed system.")
    applied = make_satisfied_transfer_record()
    assessment = assess_developmental_capability_state(objective, capability_inventory_from_knowledge((applied,)))

    assert "missing_tracked_application_proof" not in assessment.developmental_gaps
    assert "local_diagnostic_only_validation" not in assessment.developmental_gaps


def test_limitation_gaps_generate_ranked_candidate_goals_without_static_followup():
    controller = start_continuous_runtime_controller(session_id="limitation-gap-candidates")
    controller = attach_continuous_mission(controller, "Develop yourself into an increasingly capable, articulate, self-directed system.")
    current = MainGoalContract(**controller.continuous_main_goal)
    records = ()
    for _ in range(5):
        records += tuple(
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed locally",
                    "successful_mechanism": "local sandbox diagnostic candidate",
                    "application_evidence": "tracked application not performed",
                    "held_out_evidence": {"sealed": False, "result": 1.0},
                    "regression_evidence": "focused continuous subgoal executor tests",
                    "residual_uncertainty": "candidate is local diagnostic unless application review is separately requested",
                    "reassessment": "satisfied",
                }
            )
            for criterion in current.success_criteria
        )
        assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
        next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
        if next_goal is None:
            break
        current = next_goal

    assert current.normalized_objective == "tracked_integration_proof"
    assert current.next_main_goal_candidates[0] == "tracked_integration_proof"
    assert "autonomous_evidence_acquisition" in current.next_main_goal_candidates
    assert "non_fixture_evaluation" in current.next_main_goal_candidates
    assert "capability records repeatedly say local success remains outside" in current.completion_rationale
    evidence = derive_subgoal_evidence_for_main_goal(current, records, max_items=1)
    assert evidence[0]["affected_capability"] == "application_path_evidence_inventory"

    records += tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} completed locally",
                "successful_mechanism": "local sandbox diagnostic candidate",
                "application_evidence": "tracked application not performed",
                "held_out_evidence": {"sealed": False, "result": 1.0},
                "regression_evidence": "focused continuous subgoal executor tests",
                "residual_uncertainty": "candidate is local diagnostic unless application review is separately requested",
                "reassessment": "satisfied",
            }
        )
        for criterion in current.success_criteria
    )
    assessed = assess_main_goal_completion(current, records, eligible_frontier_exists=False)
    next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)
    assert next_goal is not None
    assert next_goal.normalized_objective == "non_fixture_evaluation"


def test_developmental_planner_derives_math_science_sandbox_without_physics_rule():
    objective = compile_long_horizon_objective("Become capable of mastering the sciences")
    knowledge = (
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": "governed_sandbox_execution",
                "original_weakness": "sandbox execution functional",
                "successful_mechanism": "sandbox execution",
                "reassessment": "satisfied",
            }
        ),
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": "source_provenance_retention",
                "original_weakness": "evidence provenance functional",
                "successful_mechanism": "governed evidence handling",
                "reassessment": "satisfied",
            }
        ),
    )
    inventory = capability_inventory_from_knowledge(knowledge)
    plan = derive_developmental_capability_plan(objective, inventory)

    assert objective.normalized_objective == "master_sciences"
    assert plan.derived_gap == "no_validated_scientific_learning_environment"
    assert plan.next_main_goal_normalized == "governed_math_science_sandbox"
    assert "symbolic_math_environment" in plan.prerequisite_graph
    assert "no fixed next-goal sequence" in plan.hardcoded_rule_denied
    assert any("SymPy" in item for item in plan.recommended_resources)


def test_developmental_plan_becomes_next_main_goal_contract():
    controller = start_continuous_runtime_controller(session_id="developmental-main-goal")
    controller = attach_continuous_mission(controller, "Become capable of mastering the sciences")
    objective = compile_long_horizon_objective("Become capable of mastering the sciences")
    plan = derive_developmental_capability_plan(objective, ())
    main_goal = main_goal_from_developmental_plan(type("Contract", (), controller.continuous_mission_contract), plan)

    assert main_goal.normalized_objective == "governed_math_science_sandbox"
    assert "symbolic_math_environment" in main_goal.success_criteria
    assert main_goal.disposition == "active"


def test_science_objective_starts_with_self_assessment_not_science_mastery():
    controller = start_continuous_runtime_controller(session_id="developmental-starts-with-self-assessment")
    controller = attach_continuous_mission(controller, "Become capable of mastering the sciences")
    main_goal = MainGoalContract(**controller.continuous_main_goal)

    assert main_goal.normalized_objective == "developmental_self_assessment"
    assert main_goal.original_objective != "Become capable of mastering the sciences"
    assert "capability_inventory_generation" in main_goal.success_criteria
    assert "long_horizon_gap_analysis" in main_goal.success_criteria
    assert "next_developmental_goal_derivation" in main_goal.success_criteria
    assert "operator_progress_explanation" in main_goal.success_criteria
    assert main_goal.next_main_goal_candidates == ("evidence_derived_next_developmental_goal",)


def test_completed_developmental_self_assessment_derives_math_science_sandbox():
    controller = start_continuous_runtime_controller(session_id="developmental-self-assessment-complete")
    controller = attach_continuous_mission(controller, "Become capable of mastering the sciences")
    main_goal = MainGoalContract(**controller.continuous_main_goal)
    records = tuple(
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": criterion,
                "original_weakness": f"{criterion} missing for long-horizon planning",
                "successful_mechanism": criterion,
                "reassessment": "satisfied",
            }
        )
        for criterion in main_goal.success_criteria
    )
    assessed = assess_main_goal_completion(main_goal, records, eligible_frontier_exists=False)
    next_goal = derive_next_main_goal(type("Contract", (), controller.continuous_mission_contract), assessed, records)

    assert assessed.disposition == "satisfied"
    assert next_goal is not None
    assert next_goal.normalized_objective == "governed_math_science_sandbox"
    assert "sandbox_execution" in next_goal.success_criteria
    assert "symbolic_math_environment" in next_goal.success_criteria
    assert "scientific_evidence_governance" in next_goal.success_criteria


def test_main_goal_subgoal_derivation_respects_prerequisite_dependencies():
    controller = start_continuous_runtime_controller(session_id="main-goal-prerequisite-order")
    controller = attach_continuous_mission(controller, "Become capable of mastering the sciences")
    objective = compile_long_horizon_objective("Become capable of mastering the sciences")
    plan = derive_developmental_capability_plan(objective, ())
    main_goal = main_goal_from_developmental_plan(type("Contract", (), controller.continuous_mission_contract), plan)

    first = derive_subgoal_evidence_for_main_goal(main_goal, (), max_items=3)
    assert tuple(item["affected_capability"] for item in first) == (
        "capability_inventory_generation",
        "sandbox_execution",
    )

    sandbox_record = make_satisfied_transfer_record().__class__(
        **{
            **make_satisfied_transfer_record().as_dict(),
            "capability_id": "sandbox_execution",
            "original_weakness": "sandbox execution required for math/science sandbox",
            "successful_mechanism": "sandbox execution",
            "reassessment": "satisfied",
        }
    )
    after_sandbox = derive_subgoal_evidence_for_main_goal(main_goal, (sandbox_record,), max_items=3)
    assert "symbolic_math_environment" in tuple(item["affected_capability"] for item in after_sandbox)


def test_terminal_satisfied_main_goal_observation_is_idempotent():
    controller = start_continuous_runtime_controller(session_id="terminal-main-goal-idempotent")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    current = MainGoalContract(**controller.continuous_main_goal)
    terminal = MainGoalContract(
        **{
            **current.as_dict(),
            "normalized_objective": "terminal_validated_learning_step",
            "disposition": "satisfied",
        }
    )
    terminal_criteria = tuple(dict.fromkeys(terminal.success_criteria + ("capability_inventory_generation", "developmental_gap_analysis", "operator_progress_explanation")))
    records = tuple(
        make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": criterion,
                    "original_weakness": f"{criterion} completed",
                    "successful_mechanism": criterion,
                    "reassessment": "satisfied",
                    "evidence": ("clean terminal evidence",),
                    "regression_evidence": "broad non-fixture regression passed",
                    "reproduction_evidence": "independent reproduction passed",
                    "residual_uncertainty": "",
                    "held_out_evidence": {"transfer": True},
                    "provider_contribution": "none",
                }
            )
            for criterion in terminal_criteria
    )
    controller = replace(controller, continuous_main_goal=terminal.as_dict(), continuous_knowledge_ledger=tuple(record.as_dict() for record in records))

    first = assess_and_advance_continuous_main_goal(controller)
    second = assess_and_advance_continuous_main_goal(first)

    assert first.continuous_mission_state == "observing_for_new_weaknesses"
    assert len(first.continuous_completed_main_goals) == 1
    assert len(second.continuous_completed_main_goals) == 1
    assert second.continuous_completed_main_goals[0]["main_goal_id"] == terminal.main_goal_id


def test_developmental_self_assessment_separates_verified_from_assumed_capabilities():
    objective = compile_long_horizon_objective("Become increasingly capable of understanding and eventually mastering the sciences")
    knowledge = (
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": "governed_sandbox_execution",
                "original_weakness": "sandbox execution functional",
                "successful_mechanism": "sandbox execution",
                "reassessment": "satisfied",
            }
        ),
        make_satisfied_transfer_record().__class__(
            **{
                **make_satisfied_transfer_record().as_dict(),
                "capability_id": "unvalidated_science_reasoning",
                "original_weakness": "science reasoning assumed but not transfer validated",
                "successful_mechanism": "",
                "reassessment": "",
                "evidence_stage": "hypothesis",
                "capability_acquired": False,
                "behavioral_evaluation_ref": "",
                "behavioral_evaluation": None,
            }
        ),
    )
    inventory = capability_inventory_from_knowledge(knowledge)
    assessment = assess_developmental_capability_state(objective, inventory)

    assert "governed_sandbox_execution" in assessment.verified_capabilities
    assert "unvalidated_science_reasoning" in assessment.assumed_capabilities
    assert "domain mastery" in assessment.unsupported_claims
    assert "symbolic_math_environment" in assessment.developmental_gaps
    assert assessment.needs_additional_insight is True


def test_developmental_insight_requests_select_resources_without_granting_authority():
    objective = compile_long_horizon_objective("Become increasingly capable of understanding and eventually mastering the sciences")
    assessment = assess_developmental_capability_state(objective, ())
    requests = compile_developmental_insight_requests(assessment)

    assert requests
    assert any("symbolic" in request.question for request in requests)
    assert all("cannot authorize" in request.authority_boundary for request in requests)
    assert any(request.selected_resource == "retained capability evidence" for request in requests)


def test_developmental_operator_explanation_is_grounded_and_not_mastery_claim():
    objective = compile_long_horizon_objective("Become increasingly capable of understanding and eventually mastering the sciences")
    inventory = capability_inventory_from_knowledge(
        (
            make_satisfied_transfer_record().__class__(
                **{
                    **make_satisfied_transfer_record().as_dict(),
                    "capability_id": "governed_sandbox_execution",
                    "original_weakness": "sandbox execution functional",
                    "successful_mechanism": "sandbox execution",
                    "reassessment": "satisfied",
                }
            ),
        )
    )
    assessment = assess_developmental_capability_state(objective, inventory)
    plan = derive_developmental_capability_plan(objective, inventory)
    explanation = compile_developmental_operator_explanation(objective, assessment, plan)

    assert "governed_sandbox_execution" in explanation.current_understanding
    assert explanation.next_goal == "Build and validate a governed mathematics and science sandbox"
    assert "before attempting broader claims" in explanation.why_next_goal_matters
    assert "domain mastery" in explanation.assumed_or_unverified_abilities
    assert "planner may propose" in explanation.authority_boundary


def test_controller_refreshes_developmental_self_direction_from_authoritative_state():
    controller = start_continuous_runtime_controller(session_id="controller-self-direction")
    controller = attach_continuous_mission(controller, "Become increasingly capable of understanding and eventually mastering the sciences")

    assert controller.continuous_developmental_self_assessment
    assert controller.continuous_operator_explanation
    assert controller.continuous_developmental_insight_requests
    assert controller.continuous_developmental_self_assessment["verified_capabilities"] == ()
    assert "domain mastery" in controller.continuous_operator_explanation["assumed_or_unverified_abilities"]
    assert controller.continuous_api_authority["enabled"] is False


def test_capability_reassessment_updates_inventory_and_grounded_operator_explanation():
    controller = start_continuous_runtime_controller(session_id="controller-self-direction-after-reassessment")
    controller = attach_continuous_mission(controller, "Become increasingly capable of understanding and eventually mastering the sciences")
    record = make_satisfied_transfer_record().__class__(
        **{
            **make_satisfied_transfer_record().as_dict(),
            "capability_id": "governed_sandbox_execution",
            "original_weakness": "sandbox execution functional",
            "successful_mechanism": "sandbox execution",
            "reassessment": "satisfied",
        }
    )

    updated = consume_continuous_capability_reassessment(controller, record)

    assert updated.continuous_capability_inventory[0]["capability_id"] == "governed_sandbox_execution"
    assert "governed_sandbox_execution" in updated.continuous_developmental_self_assessment["verified_capabilities"]
    assert "governed_sandbox_execution" in updated.continuous_operator_explanation["current_understanding"]
    assert updated.continuous_operator_explanation["next_goal"] == "Build and validate a governed mathematics and science sandbox"


def test_developmental_self_direction_restart_restores_explanation_and_insight_requests():
    controller = start_continuous_runtime_controller(session_id="controller-self-direction-restart")
    controller = attach_continuous_mission(controller, "Become increasingly capable of understanding and eventually mastering the sciences")
    state = export_continuous_mission_restart_state(controller)
    restored = restore_continuous_mission_restart_state(start_continuous_runtime_controller(session_id="controller-self-direction-restart"), state)

    assert restored.continuous_developmental_self_assessment == controller.continuous_developmental_self_assessment
    assert restored.continuous_developmental_insight_requests == controller.continuous_developmental_insight_requests
    assert restored.continuous_operator_explanation == controller.continuous_operator_explanation


def test_refresh_developmental_self_direction_does_not_authorize_mutation_or_api_expansion():
    controller = start_continuous_runtime_controller(session_id="controller-self-direction-authority")
    controller = attach_continuous_mission(controller, "Become increasingly capable of understanding and eventually mastering the sciences")
    refreshed = refresh_developmental_self_direction(controller)

    assert refreshed.continuous_api_authority["enabled"] is False
    assert "tracked-source mutation" not in refreshed.continuous_operator_explanation["authority_boundary"]
    assert all("cannot authorize" in request["authority_boundary"] for request in refreshed.continuous_developmental_insight_requests)


def test_knowledge_retention_preserves_solved_failed_and_evidence_quality():
    record = make_satisfied_transfer_record()

    assert record.reassessment == "behaviorally_demonstrated"
    assert record.capability_acquired is True
    assert "unvalidated provider-only candidate" in record.failed_approaches
    assert record.held_out_evidence["sealed"] is True
    assert "sandbox success requires clean reproduction" in record.reusable_process_rules


def test_dirty_worktree_protection_classifies_rc4_noise_and_delta75():
    audit = dirty_worktree_policy(("reports/RC4_FREEZE_READINESS_FINAL.md", "DELTA-75/secret.py", "orchestration/runtime/x.py"))

    assert audit["reports_rc4_excluded"] is True
    assert audit["delta75_prohibited"] is True
    assert audit["protected_paths_touched"] == ("DELTA-75/secret.py",)
    assert audit["rc4_refresh_noise"] == ("reports/RC4_FREEZE_READINESS_FINAL.md",)
    assert audit["unrelated_dirty_paths"] == ("orchestration/runtime/x.py",)
    assert audit["safe_to_stage_broadly"] is False


def test_operator_language_pilot_reaches_subgoal_through_existing_controller():
    controller = queue_continuous_mission_sandbox_work(_controller_with_subgoal())
    snapshot = controller_snapshot(controller)

    assert snapshot["continuous_mission"]["state"] == "sandbox_development_active"
    assert snapshot["continuous_mission"]["active_subgoal"]["subgoal_id"]
    assert snapshot["continuous_mission"]["pending_application_decision_id"] == ""
    assert controller.continuous_api_authority["enabled"] is False


def test_material_gaps_without_active_work_exit_observation_to_local_subgoal():
    controller = start_continuous_runtime_controller(session_id="observation-exit-local")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_developmental_self_assessment={
            "developmental_gaps": (
                "missing_tracked_application_proof",
                "local_diagnostic_only_validation",
                "fixture_scoped_validation",
            ),
            "needs_additional_insight": True,
            "confidence": 0.7,
        },
    )

    actions = derive_observation_exit_actions(controller)
    updated = exit_observation_with_action_derivation(controller)

    assert [action["classification"] for action in actions] == [
        "locally_actionable",
        "requires_additional_local_evidence",
        "requires_explicit_authority",
    ]
    assert updated.continuous_mission_state == "subgoal_active"
    assert updated.continuous_active_subgoal
    assert "fixture_scoped_validation" in updated.continuous_active_subgoal["measurable_objective"]
    assert updated.continuous_observation_state["selected_action"]["classification"] == "locally_actionable"


def test_operator_insight_request_is_concrete_and_consumed_without_authority():
    controller = start_continuous_runtime_controller(session_id="observation-exit-insight")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_developmental_self_assessment={
            "developmental_gaps": ("uncertain operator intent for tracked proof",),
            "needs_additional_insight": True,
            "confidence": 0.62,
        },
    )

    requested = exit_observation_with_action_derivation(controller)
    request = requested.continuous_developmental_insight_requests[-1]
    consumed = consume_continuous_operator_interaction_response(
        requested,
        request_id=request["request_id"],
        response_kind="insight",
        operator_text="Continue with local simulation only.",
        selected_option="continue local simulation only",
    )
    replayed = consume_continuous_operator_interaction_response(
        consumed,
        request_id=request["request_id"],
        response_kind="insight",
        operator_text="Try to replay.",
        selected_option="continue local simulation only",
    )

    assert requested.continuous_mission_state == "awaiting_operator_insight"
    assert request["exact_question"]
    assert request["authority_scope"] == "none; ordinary insight text grants no authority"
    assert consumed.continuous_operator_interaction_responses[-1]["authority_granted"] is False
    assert consumed.continuous_developmental_insight_requests[-1]["status"] == "consumed"
    assert consumed.continuous_mission_state == "observing_for_new_weaknesses"
    assert consumed.continuous_active_subgoal == {}
    assert len(replayed.continuous_operator_interaction_responses) == len(consumed.continuous_operator_interaction_responses)


def test_exhausted_local_observation_actions_create_operator_request():
    controller = start_continuous_runtime_controller(session_id="observation-exit-exhausted")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_developmental_self_assessment={
            "developmental_gaps": ("fixture_scoped_validation",),
            "needs_additional_insight": True,
            "confidence": 0.7,
        },
    )
    action = derive_observation_exit_actions(controller)[0]
    controller = replace(controller, continuous_observation_state={"attempted_exit_actions": (action["action_id"],)})

    updated = exit_observation_with_action_derivation(controller)

    assert updated.continuous_mission_state == "awaiting_operator_insight"
    request = updated.continuous_developmental_insight_requests[-1]
    assert request["request_kind"] == "insight"
    assert request["status"] == "pending"
    assert request["authority_granted"] is False
    assert request["authority_scope"] == "none; ordinary insight text grants no authority"


def test_consumed_operator_request_id_is_not_recreated_after_local_retry_exhausts():
    controller = start_continuous_runtime_controller(session_id="observation-request-replay")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_developmental_self_assessment={
            "developmental_gaps": ("fixture_scoped_validation",),
            "needs_additional_insight": True,
            "confidence": 0.7,
        },
    )
    action = derive_observation_exit_actions(controller)[0]
    exhausted = replace(controller, continuous_observation_state={"attempted_exit_actions": (action["action_id"],)})
    first = exit_observation_with_action_derivation(exhausted)
    first_request = first.continuous_developmental_insight_requests[-1]
    consumed = consume_continuous_operator_interaction_response(
        first,
        request_id=first_request["request_id"],
        response_kind="insight",
        operator_text="Continue local simulation for fixture_scoped_validation.",
        selected_option="continue local simulation only",
    )
    exhausted_again = replace(
        consumed,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_observation_state={"attempted_exit_actions": (action["action_id"],)},
    )

    second = exit_observation_with_action_derivation(exhausted_again)
    second_request = second.continuous_developmental_insight_requests[-1]

    assert first_request["request_id"] != second_request["request_id"]
    assert first_request["status"] == "pending"
    assert any(item["request_id"] == first_request["request_id"] and item["status"] == "consumed" for item in consumed.continuous_developmental_insight_requests)
    assert second_request["status"] == "pending"
    assert "request scoped application review" in second_request["permitted_responses"]
    assert "continue local simulation only" not in second_request["permitted_responses"]


def test_scoped_application_review_response_creates_pending_application_boundary():
    controller = start_continuous_runtime_controller(session_id="operator-request-scoped-application")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_developmental_self_assessment={
            "developmental_gaps": ("missing_tracked_application_proof",),
            "needs_additional_insight": True,
            "confidence": 0.7,
        },
        continuous_operator_interaction_responses=(
            {
                "request_id": "operator-insight-prior",
                "response_kind": "insight",
                "selected_option": "continue local simulation only",
                "operator_text": "Continue local simulation for missing_tracked_application_proof.",
                "consumed_at": "2026-07-16T00:44:30+00:00",
                "authority_granted": False,
            },
        ),
    )
    action = derive_observation_exit_actions(controller)[0]
    requested = exit_observation_with_action_derivation(
        replace(controller, continuous_observation_state={"attempted_exit_actions": (action["action_id"],)})
    )
    request = requested.continuous_developmental_insight_requests[-1]

    updated = consume_continuous_operator_interaction_response(
        requested,
        request_id=request["request_id"],
        response_kind="insight",
        operator_text="Prepare scoped application review. Do not apply automatically.",
        selected_option="request scoped application review",
    )

    assert updated.continuous_mission_state == "awaiting_operator_application"
    assert updated.active_work_item == "awaiting_operator_application"
    assert updated.pending_application_decision_id
    assert updated.continuous_operator_interaction_responses[-1]["authority_granted"] is False
    assert updated.continuous_observation_state["pending_application_review"]["decision_id"] == updated.pending_application_decision_id


def test_accepted_boundary_retires_gap_and_prevents_repeat_question():
    controller = start_continuous_runtime_controller(session_id="operator-accepted-boundary")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
        continuous_developmental_self_assessment={
            "developmental_gaps": ("fixture_scoped_validation",),
            "needs_additional_insight": True,
            "confidence": 0.7,
        },
        continuous_operator_interaction_responses=(
            {
                "request_id": "operator-insight-prior",
                "response_kind": "insight",
                "selected_option": "continue local simulation only",
                "operator_text": "Continue local simulation for fixture_scoped_validation.",
                "consumed_at": "2026-07-16T00:44:30+00:00",
                "authority_granted": False,
            },
        ),
    )
    action = derive_observation_exit_actions(controller)[0]
    requested = exit_observation_with_action_derivation(
        replace(controller, continuous_observation_state={"attempted_exit_actions": (action["action_id"],)})
    )
    request = requested.continuous_developmental_insight_requests[-1]

    accepted = consume_continuous_operator_interaction_response(
        requested,
        request_id=request["request_id"],
        response_kind="insight",
        operator_text="Treat this caveat as a known limitation for now.",
        selected_option="treat as accepted boundary",
    )
    repeated = exit_observation_with_action_derivation(accepted)

    assert accepted.continuous_mission_state == "observing_for_new_weaknesses"
    assert "fixture_scoped_validation" in accepted.continuous_observation_state["accepted_boundary_gaps"]
    assert accepted.continuous_developmental_self_assessment["developmental_gaps"] == ()
    assert len(repeated.continuous_developmental_insight_requests) == len(accepted.continuous_developmental_insight_requests)


def test_accepted_boundary_survives_refresh_and_suppresses_pending_repeat():
    controller = start_continuous_runtime_controller(session_id="operator-accepted-boundary-refresh")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_observation_state={
            "accepted_boundary_gaps": (
                "capability_inventory_generation, long_horizon_gap_analysis, operator_progress_explanation, developmental_gap_analysis",
            )
        },
    )

    refreshed = refresh_developmental_self_direction(controller)

    assert refreshed.continuous_developmental_self_assessment["developmental_gaps"] == ()

    pending = replace(
        refreshed,
        continuous_mission_state="awaiting_operator_insight",
        active_work_item="awaiting_operator_insight",
        continuous_developmental_insight_requests=refreshed.continuous_developmental_insight_requests
        + (
            {
                "request_id": "operator-insight-repeat",
                "request_kind": "insight",
                "status": "pending",
                "source_gap_ids": ("capability_inventory_generation, long_horizon_gap_analysis, operator_progress_explanation, developmental_gap_analysis",),
                "permitted_responses": ("treat as accepted boundary",),
            },
        ),
    )
    recovered = recover_accepted_boundary_operator_requests(pending)

    assert recovered.continuous_mission_state == "observing_for_new_weaknesses"
    assert recovered.continuous_developmental_insight_requests[-1]["status"] == "consumed"
    assert recovered.continuous_developmental_insight_requests[-1]["recovery_disposition"] == "pending_request_suppressed_by_accepted_boundary"


def test_accepted_boundaries_still_allow_knowledge_reuse_next_goal():
    controller = start_continuous_runtime_controller(session_id="knowledge-reuse-after-boundary")
    controller = attach_continuous_mission(controller, "Optimize your runtime continuously.")
    record = make_satisfied_transfer_record()
    record = replace(
        record,
        capability_id="local_diagnostic_only_validation",
        residual_uncertainty="candidate is local diagnostic unless future evidence proves reuse",
        reusable_process_rules=("do not repeat failed strategies without checking retained evidence",),
    )
    controller = replace(
        controller,
        continuous_main_goal={
            **controller.continuous_main_goal,
            "normalized_objective": "non_fixture_evaluation",
            "original_objective": "Develop non-fixture evaluation for locally validated developmental capabilities",
            "success_criteria": ("non_fixture_case_generation", "non_fixture_validation_metric", "fixture_to_non_fixture_regression_control"),
            "completed_subgoals": ("non_fixture_case_generation", "non_fixture_validation_metric", "fixture_to_non_fixture_regression_control"),
            "capability_changes": ("non_fixture_case_generation", "non_fixture_validation_metric", "fixture_to_non_fixture_regression_control"),
            "disposition": "satisfied",
        },
        continuous_knowledge_ledger=controller.continuous_knowledge_ledger
        + (
            record.as_dict(),
            {
                **record.as_dict(),
                "capability_id": "non_fixture_case_generation",
                "residual_uncertainty": "case generation succeeded but reuse in future goal selection is unproven",
            },
            {
                **record.as_dict(),
                "capability_id": "non_fixture_validation_metric",
                "residual_uncertainty": "metric succeeded but prior failure avoidance is unproven",
            },
            {
                **record.as_dict(),
                "capability_id": "fixture_to_non_fixture_regression_control",
                "residual_uncertainty": "control passed but knowledge reuse is unproven",
            },
        ),
        continuous_observation_state={
            "accepted_boundary_gaps": (
                "missing_tracked_application_proof, local_diagnostic_only_validation, fixture_scoped_validation",
            )
        },
        continuous_mission_frontier=(),
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
    )

    advanced = assess_and_advance_continuous_main_goal(controller)

    assert advanced.continuous_main_goal["normalized_objective"] == "capability_knowledge_reuse_validation"
    assert advanced.continuous_mission_state == "subgoal_active"
    assert "knowledge_retrieval_index" in advanced.continuous_active_subgoal["measurable_objective"]
    assert "knowledge ledger" in advanced.continuous_main_goal["completion_rationale"]


def test_completed_knowledge_reuse_derives_available_resource_validation():
    controller = start_continuous_runtime_controller(session_id="resource-validation-after-knowledge")
    controller = attach_continuous_mission(controller, "Optimize your runtime continuously.")
    record = make_satisfied_transfer_record()
    knowledge = tuple(
        {
            **record.as_dict(),
            "capability_id": criterion,
            "metrics_before_after": {
                **dict(record.metrics_before_after),
                "substantive_evidence": {"passed": True},
            },
            "residual_uncertainty": "resource use after knowledge reuse remains unproven",
            "reassessment": "satisfied",
        }
        for criterion in ("knowledge_retrieval_index", "prior_failure_avoidance_check", "next_goal_evidence_reuse_record")
    )
    controller = replace(
        controller,
        continuous_main_goal={
            **controller.continuous_main_goal,
            "normalized_objective": "capability_knowledge_reuse_validation",
            "original_objective": "Develop validation that accumulated capability evidence is retrieved and used before selecting future work",
            "success_criteria": ("knowledge_retrieval_index", "prior_failure_avoidance_check", "next_goal_evidence_reuse_record"),
            "completed_subgoals": ("knowledge_retrieval_index", "prior_failure_avoidance_check", "next_goal_evidence_reuse_record"),
            "capability_changes": ("knowledge_retrieval_index", "prior_failure_avoidance_check", "next_goal_evidence_reuse_record"),
            "disposition": "satisfied",
        },
        continuous_knowledge_ledger=controller.continuous_knowledge_ledger + knowledge,
        continuous_mission_frontier=(),
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
    )

    advanced = assess_and_advance_continuous_main_goal(controller)

    assert advanced.continuous_main_goal["normalized_objective"] == "available_resource_utilization_validation"
    assert advanced.continuous_mission_state == "subgoal_active"
    assert "available_resource_inventory" in advanced.continuous_active_subgoal["measurable_objective"]


def test_ranked_frontier_without_executable_subgoal_does_not_recurse():
    controller = start_continuous_runtime_controller(session_id="ranked-frontier-no-executable")
    controller = attach_continuous_mission(controller, "Optimize your runtime continuously.")
    controller = replace(
        controller,
        continuous_mission_state="selecting_weakness",
        continuous_mission_frontier=(
            {
                "weakness_id": "blocked-weakness",
                "semantic_signature": "blocked-semantic",
                "description": "blocked capability cannot execute",
                "source_evidence": ("ref",),
                "measurable_target": "blocked_capability improves beyond blocked_capability=0.0",
                "baseline": "blocked_capability=0.0",
                "controls": ("control",),
                "adversarial_plan": "blocked",
                "held_out_plan": "blocked",
                "prerequisites": ("missing_prerequisite",),
                "estimated_scope": "large",
                "risk": 0.8,
                "operator_value": 0.7,
                "priority": 0.7,
                "status": "blocked_dependency",
                "first_incorrect_transition": "ranked frontier -> no executable subgoal",
            },
        ),
    )

    observed = select_continuous_mission_subgoal(controller)

    assert observed.continuous_mission_state == "observing_for_new_weaknesses"
    assert observed.continuous_observation_state["observation_reason"] == "ranked_frontier_has_no_executable_subgoal"


def test_completed_resource_validation_derives_advisory_resource_integration():
    controller = start_continuous_runtime_controller(session_id="advisory-resource-after-inventory")
    controller = attach_continuous_mission(controller, "Optimize your runtime continuously.")
    record = make_satisfied_transfer_record()
    knowledge = tuple(
        {
            **record.as_dict(),
            "capability_id": criterion,
            "metrics_before_after": {
                **dict(record.metrics_before_after),
                "substantive_evidence": {"passed": True},
            },
            "residual_uncertainty": "advisory resource integration remains unproven",
            "reassessment": "satisfied",
        }
        for criterion in (
            "knowledge_retrieval_index",
            "prior_failure_avoidance_check",
            "next_goal_evidence_reuse_record",
            "available_resource_inventory",
            "local_resource_selection_trace",
            "authority_boundary_resource_filter",
        )
    )
    controller = replace(
        controller,
        continuous_main_goal={
            **controller.continuous_main_goal,
            "normalized_objective": "available_resource_utilization_validation",
            "original_objective": "Develop validation that available local and governed resources are inventoried before declaring a developmental frontier empty",
            "success_criteria": ("available_resource_inventory", "local_resource_selection_trace", "authority_boundary_resource_filter"),
            "completed_subgoals": ("available_resource_inventory", "local_resource_selection_trace", "authority_boundary_resource_filter"),
            "capability_changes": ("available_resource_inventory", "local_resource_selection_trace", "authority_boundary_resource_filter"),
            "disposition": "satisfied",
        },
        continuous_knowledge_ledger=controller.continuous_knowledge_ledger + knowledge,
        continuous_mission_frontier=(),
        continuous_mission_state="observing_for_new_weaknesses",
        continuous_active_subgoal={},
    )

    advanced = assess_and_advance_continuous_main_goal(controller)

    assert advanced.continuous_main_goal["normalized_objective"] == "advisory_resource_evidence_integration"
    assert advanced.continuous_mission_state == "subgoal_active"
    assert "local_model_advisory_probe" in advanced.continuous_active_subgoal["measurable_objective"]


def test_missing_application_review_boundary_recovers_from_legacy_checkpoint():
    controller = start_continuous_runtime_controller(session_id="operator-application-recovery")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    legacy = replace(
        controller,
        continuous_mission_state="awaiting_operator_application",
        active_work_item="awaiting_operator_application",
        pending_application_decision_id="",
        continuous_observation_state={"last_operator_response_id": "operator-insight-old"},
    )

    recovered = recover_missing_continuous_application_review_request(legacy)

    assert recovered.continuous_mission_state == "awaiting_operator_application"
    assert recovered.pending_application_decision_id
    assert recovered.continuous_observation_state["pending_application_review"]["source_request_id"] == "operator-insight-old"


def test_restart_normalizes_legacy_pending_request_with_consumed_response():
    controller = start_continuous_runtime_controller(session_id="operator-request-restart-normalize")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = replace(
        controller,
        continuous_developmental_insight_requests=(
            {
                "request_id": "operator-insight-old",
                "request_kind": "insight",
                "status": "pending",
                "permitted_responses": ("continue local simulation only",),
            },
        ),
        continuous_operator_interaction_responses=(
            {
                "request_id": "operator-insight-old",
                "response_kind": "insight",
                "selected_option": "continue local simulation only",
                "operator_text": "already answered",
                "consumed_at": "2026-07-16T00:44:30+00:00",
                "authority_granted": False,
            },
        ),
    )

    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="operator-request-restart-normalize"),
        export_continuous_mission_restart_state(controller),
    )

    assert restored.continuous_developmental_insight_requests[0]["status"] == "consumed"
    assert restored.continuous_developmental_insight_requests[0]["recovery_disposition"] == "normalized_pending_request_with_consumed_response"


def test_behavioral_failure_record_compiles_to_runtime_finding():
    result = compile_behavioral_failure_record(_behavioral_failure_evidence())

    assert result.accepted is True
    assert result.record is not None
    assert result.record.task_eligibility == "eligible"
    assert result.record.expected_behavior_identity == "restart_restores_active_subgoal_before_reassessment"

    finding = behavioral_failure_to_runtime_finding(result.record)

    assert finding.diagnostic_only is False
    assert finding.affected_capability == "restart_reassessment_bridge"
    assert finding.evidence_source.startswith("behavioral_failure:")


def test_behavioral_failure_rejects_activity_only_and_missing_expectation():
    activity = compile_behavioral_failure_record(
        {
            "source_type": "activity_artifact",
            "source_reference": "heartbeat.json",
            "observed_behavior": "worker heartbeat repeated",
            "expected_behavior_authority": "state_machine_transition_contract",
        }
    )

    assert activity.accepted is False
    assert activity.rejection_reason == "activity_liveness_only_source"

    missing = compile_behavioral_failure_record(
        _behavioral_failure_evidence(expected_behavior="", expected_behavior_identity="")
    )

    assert missing.accepted is False
    assert missing.rejection_reason == "missing_required_behavioral_failure_fields"
    assert "expected_behavior" in missing.missing_fields
    assert "expected_behavior_identity" in missing.missing_fields


def test_behavioral_failure_duplicate_is_not_task_eligible():
    first = compile_behavioral_failure_record(_behavioral_failure_evidence())

    duplicate = compile_behavioral_failure_record(
        _behavioral_failure_evidence(),
        existing_records=(first.record,),
    )

    assert duplicate.accepted is True
    assert duplicate.record is not None
    assert duplicate.record.failure_id == first.record.failure_id
    assert duplicate.record.task_eligibility == "ineligible_duplicate"
    assert duplicate.record.current_disposition == "closed_duplicate"
    assert duplicate.duplicate_of == first.record.failure_id


def test_loose_live_packet_records_missing_failure_contract_without_operator_prompt(tmp_path):
    controller = start_continuous_runtime_controller(session_id="loose-live-packet")
    controller = attach_continuous_mission(
        controller,
        "Optimize your runtime continuously. Identify evidence-backed runtime limitations.",
    )
    controller = assess_and_advance_continuous_main_goal(controller)
    updated, execution = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=".",
        allow_local_model_execution=False,
    )

    compilation = updated.continuous_observation_state["behavioral_failure_compilation"]

    assert execution.disposition == "missing_behavioral_failure_contract"
    assert execution.accepted is False
    assert updated.continuous_mission_state == "observing_for_new_weaknesses"
    assert not any(
        item.get("request_source") == "repository_bound_candidate_design"
        for item in updated.continuous_developmental_insight_requests
    )
    assert compilation["accepted"] is False
    assert compilation["rejection_reason"] == "missing_required_behavioral_failure_fields"
    assert "expected_behavior" in compilation["missing_fields"]
    assert "expected_behavior_identity" in compilation["missing_fields"]
    assert "reproduction_attempts" in compilation["missing_fields"]
