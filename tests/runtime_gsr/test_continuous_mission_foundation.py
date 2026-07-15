from dataclasses import replace

import pytest

from orchestration.runtime.continuous_mission_foundation import (
    OBSERVATION_STATE,
    MainGoalContract,
    assess_main_goal_completion,
    capability_inventory_from_knowledge,
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
    rank_weakness_frontier,
)
from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_runtime,
    attach_continuous_mission,
    consume_continuous_capability_reassessment,
    consume_continuous_mission_application_decision,
    continue_continuous_mission_after_reassessment,
    controller_snapshot,
    export_continuous_mission_restart_state,
    mark_continuous_api_unavailable,
    pause_continuous_mission_for_application,
    queue_continuous_mission_sandbox_work,
    refresh_continuous_mission_frontier,
    restore_continuous_mission_restart_state,
    assess_and_advance_continuous_main_goal,
    refresh_developmental_self_direction,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)


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
    completed_next_goal = assess_main_goal_completion(next_goal, completion_records, eligible_frontier_exists=False)
    assert "prior_active_rationale=selected from ranked developmental next-goal candidates" in completed_next_goal.completion_rationale
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
        for criterion in terminal.success_criteria
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

    assert record.reassessment == "satisfied"
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
