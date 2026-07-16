from dataclasses import replace

from orchestration.runtime.continuous_mission_foundation import (
    compile_behavioral_failure_record,
    behavioral_failure_to_runtime_finding,
    rank_weakness_frontier,
)
from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_behavioral_failures,
    attach_continuous_mission,
    export_continuous_mission_restart_state,
    refresh_continuous_mission_frontier,
    restore_continuous_mission_restart_state,
    start_continuous_runtime_controller,
)


def _attempt(**overrides):
    data = {
        "command_or_predicate_identity": "pytest tests/runtime_gsr/test_existing_behavior.py::test_restart_transition",
        "input_or_state_reference": "sealed-state:restart-transition-fixture",
        "started_at": "2026-07-16T00:00:00+00:00",
        "completed_at": "2026-07-16T00:00:02+00:00",
        "status": "completed",
        "result_classification": "expected_state_not_reached",
        "stdout_digest": "stdout-digest",
        "stderr_digest": "stderr-digest",
        "result_digest": "result-digest",
        "environment_digest": "env-digest",
        "authoritative_runner_identity": "pytest-focused-existing-test",
    }
    data.update(overrides)
    return data


def _evidence(**overrides):
    data = {
        "source_type": "failing_test",
        "source_reference": "tests/runtime_gsr/test_existing_behavior.py::test_restart_transition",
        "source_digest": "source-digest-001",
        "observed_behavior": "Restart leaves the capability reassessment transition without a selected next subgoal.",
        "expected_behavior": "Restarted controller must recover the same reassessment state and either select the next legal subgoal or record a blocker.",
        "expected_behavior_identity": "continuous_restart_reassessment_contract",
        "expected_behavior_authority": "preexisting_test_assertion",
        "expected_vs_observed_result": "wrong_state_after_restart",
        "baseline_reproduction": "restart_reassessment_transition=0.0",
        "reproduction_command_or_predicate": "pytest tests/runtime_gsr/test_existing_behavior.py::test_restart_transition",
        "reproduction_attempts": (_attempt(),),
        "reproduction_result": "failed",
        "reproduction_output_digest": "repro-output-digest-001",
        "first_incorrect_transition": "restart state restored -> reassessment transition not resumed",
        "affected_runtime_stage": "restart_recovery",
        "affected_capability_id": "continuous_reassessment_consumption",
        "originating_mission_id": "mission-continuous-test",
        "suspected_owner_paths": ("orchestration/runtime/continuous_runtime_controller.py",),
        "independent_evidence_paths": ("tests/runtime_gsr/test_existing_behavior.py",),
        "allowed_scope": ("orchestration/runtime/continuous_runtime_controller.py",),
        "excluded_scope": ("DELTA-75", "reports/RC4_*"),
        "materiality_reason": "Without this transition, completed capability evidence cannot return to autonomous next-goal selection.",
        "reproducibility_status": "reproduced",
        "environment_digest": "env-digest",
        "state_digest": "state-digest",
        "authority_class": "local_execution_allowed",
        "ambiguity_status": "resolved",
        "observed_at": "2026-07-16T00:00:03+00:00",
    }
    data.update(overrides)
    return data


def _compiled(**overrides):
    result = compile_behavioral_failure_record(_evidence(**overrides))
    assert result.accepted, result.as_dict()
    assert result.record is not None
    return result.record


def test_preexisting_failing_test_evidence_compiles_to_behavioral_failure_record():
    result = compile_behavioral_failure_record(_evidence())

    assert result.accepted
    assert result.record is not None
    assert result.record.failure_id
    assert result.record.source_type == "failing_test"
    assert result.record.task_eligibility == "eligible"
    assert result.record.current_disposition == "task_eligible"
    assert result.record.sealed_failure_bundle_digest


def test_missing_expected_behavior_is_rejected():
    result = compile_behavioral_failure_record(_evidence(expected_behavior=""))

    assert not result.accepted
    assert "expected_behavior" in result.missing_fields


def test_missing_expected_behavior_identity_is_rejected():
    result = compile_behavioral_failure_record(_evidence(expected_behavior_identity=""))

    assert not result.accepted
    assert "expected_behavior_identity" in result.missing_fields


def test_missing_first_incorrect_transition_is_rejected():
    result = compile_behavioral_failure_record(_evidence(first_incorrect_transition=""))

    assert not result.accepted
    assert "first_incorrect_transition" in result.missing_fields


def test_missing_source_digest_is_rejected():
    result = compile_behavioral_failure_record(_evidence(source_digest=""))

    assert not result.accepted
    assert "source_digest" in result.missing_fields


def test_activity_only_checkpoint_and_heartbeat_evidence_are_rejected():
    checkpoint = compile_behavioral_failure_record(_evidence(source_type="activity_artifact", source_reference="checkpoint_004.json"))
    heartbeat = compile_behavioral_failure_record(_evidence(source_type="activity_artifact", source_reference="heartbeat.json"))

    assert not checkpoint.accepted
    assert checkpoint.rejection_reason == "activity_liveness_only_source"
    assert not heartbeat.accepted
    assert heartbeat.rejection_reason == "activity_liveness_only_source"


def test_model_advisory_failure_alone_is_rejected():
    result = compile_behavioral_failure_record(_evidence(source_type="model_advisory"))

    assert not result.accepted
    assert result.rejection_reason == "invalid_developmental_evidence_source"


def test_structural_only_operator_report_is_not_task_eligible():
    result = compile_behavioral_failure_record(_evidence(source_type="operator_report"))

    assert result.accepted
    assert result.record is not None
    assert result.record.task_eligibility == "ineligible_structural_only"


def test_unreproduced_retained_failure_is_not_task_eligible():
    result = compile_behavioral_failure_record(_evidence(
        source_type="retained_behavioral_evaluation_failure",
        reproducibility_status="not_reproduced",
        reproduction_result="passed",
    ))

    assert result.accepted
    assert result.record is not None
    assert result.record.task_eligibility == "ineligible_unreproduced"


def test_reproduced_material_failure_is_task_eligible():
    record = _compiled()

    assert record.task_eligibility == "eligible"
    assert record.current_disposition == "task_eligible"


def test_candidate_and_patch_payloads_are_rejected_anywhere_in_evidence():
    top_level = compile_behavioral_failure_record(_evidence(patch_text="append this"))
    nested = compile_behavioral_failure_record(_evidence(metadata={"candidate_code": "print('no')"}))

    assert not top_level.accepted
    assert top_level.rejection_reason == "forbidden_candidate_or_patch_content"
    assert not nested.accepted
    assert nested.rejection_reason == "forbidden_candidate_or_patch_content"


def test_candidate_authored_expected_behavior_is_rejected():
    result = compile_behavioral_failure_record(_evidence(candidate_authored_success_criteria="candidate says it works"))

    assert not result.accepted
    assert result.rejection_reason == "forbidden_candidate_or_patch_content"


def test_same_semantic_changed_evidence_creates_version_and_increments_occurrence():
    first = _compiled()
    second = compile_behavioral_failure_record(
        _evidence(source_digest="source-digest-002", reproduction_output_digest="repro-output-digest-002"),
        existing_records=(first,),
    )

    assert second.accepted
    assert second.record is not None
    assert second.record.semantic_failure_key == first.semantic_failure_key
    assert second.record.version_of == first.failure_id
    assert second.record.occurrence_count == 2


def test_same_evidence_replay_is_idempotent_duplicate():
    first = _compiled()
    replay = compile_behavioral_failure_record(_evidence(), existing_records=(first,))

    assert replay.accepted
    assert replay.record is not None
    assert replay.record.failure_id == first.failure_id
    assert replay.record.duplicate_of == first.failure_id
    assert replay.record.task_eligibility == "ineligible_duplicate"
    assert replay.record.occurrence_count == first.occurrence_count


def test_cosmetic_wording_does_not_create_new_semantic_failure():
    first = _compiled()
    cosmetic = compile_behavioral_failure_record(
        _evidence(
            observed_behavior="After restart, reassessment still does not resume into the expected next legal subgoal.",
            source_digest="source-digest-cosmetic",
            reproduction_output_digest="repro-output-digest-cosmetic",
        ),
        existing_records=(first,),
    )

    assert cosmetic.accepted
    assert cosmetic.record is not None
    assert cosmetic.record.semantic_failure_key == first.semantic_failure_key
    assert cosmetic.record.version_of == first.failure_id


def test_changed_first_incorrect_transition_creates_distinct_semantic_failure():
    first = _compiled()
    changed = compile_behavioral_failure_record(
        _evidence(
            first_incorrect_transition="restored reassessment state -> duplicate operator request emitted",
            source_digest="source-digest-transition-change",
        ),
        existing_records=(first,),
    )

    assert changed.accepted
    assert changed.record is not None
    assert changed.record.semantic_failure_key != first.semantic_failure_key
    assert changed.record.version_of == ""


def test_restart_round_trip_preserves_record_without_duplicate_task_creation():
    record = _compiled()
    controller = start_continuous_runtime_controller(session_id="behavioral-failure-restart")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_behavioral_failures(controller, (record,))
    state = export_continuous_mission_restart_state(controller)

    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="behavioral-failure-restart"),
        state,
    )

    assert len(restored.continuous_behavioral_failure_records) == 1
    assert restored.continuous_behavioral_failure_records[0]["failure_id"] == record.failure_id
    assert len(restored.continuous_mission_findings) == 1


def test_corrupt_persisted_record_fails_closed_on_restore():
    controller = start_continuous_runtime_controller(session_id="behavioral-failure-corrupt")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    state = export_continuous_mission_restart_state(controller)
    state["continuous_behavioral_failure_records"] = ({"failure_id": "missing-required-fields"},)

    restored = restore_continuous_mission_restart_state(
        start_continuous_runtime_controller(session_id="behavioral-failure-corrupt"),
        state,
    )

    assert restored.continuous_behavioral_failure_records == ()


def test_eligible_record_converts_into_runtime_finding_with_failure_identity():
    record = _compiled()
    finding = behavioral_failure_to_runtime_finding(record)

    assert finding.evidence_source.startswith(f"behavioral_failure:{record.failure_id}:")
    assert record.sealed_failure_bundle_digest in finding.evidence_source
    assert finding.diagnostic_only is False
    assert finding.first_incorrect_transition == record.first_incorrect_transition


def test_ineligible_record_does_not_enter_frontier():
    ineligible = _compiled(source_type="operator_report")
    controller = start_continuous_runtime_controller(session_id="behavioral-failure-ineligible")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_behavioral_failures(controller, (ineligible,))
    controller = refresh_continuous_mission_frontier(controller)

    assert controller.continuous_behavioral_failure_records
    assert controller.continuous_mission_findings == ()
    assert controller.continuous_mission_frontier == ()


def test_compiler_stops_before_active_subgoal_candidate_pcm_or_application_creation():
    record = _compiled()
    controller = start_continuous_runtime_controller(session_id="behavioral-failure-no-downstream")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_behavioral_failures(controller, (record,))

    assert controller.continuous_mission_findings
    assert controller.continuous_active_subgoal == {}
    assert controller.active_work_item == ""
    assert controller.pending_application_decision_id == ""
    assert "sandbox" not in " ".join(item["summary"] for item in controller.journal).lower()


def test_eligible_record_can_be_ranked_only_after_explicit_frontier_refresh():
    record = _compiled()
    finding = behavioral_failure_to_runtime_finding(record)
    frontier = rank_weakness_frontier((finding,))

    assert len(frontier) == 1
    assert frontier[0].source_evidence == (finding.evidence_source,)
    assert frontier[0].status == "eligible"
