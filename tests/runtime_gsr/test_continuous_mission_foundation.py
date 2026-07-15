from dataclasses import replace

import pytest

from orchestration.runtime.continuous_mission_foundation import (
    OBSERVATION_STATE,
    dirty_worktree_policy,
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
    assert continued.continuous_mission_state == "observing_for_new_weaknesses"
    assert continued.active_work_item == OBSERVATION_STATE


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

    assert observed.continuous_mission_state == "observing_for_new_weaknesses"
    assert observed.active_work_item == OBSERVATION_STATE
    reactivated = select_continuous_mission_subgoal(
        refresh_continuous_mission_frontier(assess_continuous_mission_runtime(observed, _evidence()))
    )
    assert reactivated.continuous_active_subgoal


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
