from dataclasses import replace
from pathlib import Path

from orchestration.runtime.continuous_mission_foundation import compile_behavioral_failure_record
from orchestration.runtime.continuous_runtime_controller import (
    assess_continuous_mission_behavioral_failures,
    attach_continuous_mission,
    refresh_continuous_mission_frontier,
    select_continuous_mission_subgoal,
    start_continuous_runtime_controller,
)
from orchestration.runtime.continuous_subgoal_executor import (
    compile_repository_behavior_contract,
    execute_continuous_active_subgoal,
)


def _attempt(**overrides):
    data = {
        "command_or_predicate_identity": "pytest tests/test_sample.py::test_missing_guard",
        "input_or_state_reference": "sealed-state:missing-guard",
        "started_at": "2026-07-16T00:00:00+00:00",
        "completed_at": "2026-07-16T00:00:01+00:00",
        "status": "completed",
        "result_classification": "expected_symbol_missing",
        "result_digest": "result-digest",
        "environment_digest": "env-digest",
        "authoritative_runner_identity": "focused-test-runner",
    }
    data.update(overrides)
    return data


def _failure_evidence(**overrides):
    data = {
        "source_type": "failing_test",
        "source_reference": "tests/test_sample.py::test_missing_guard",
        "source_digest": "source-digest",
        "observed_behavior": "sample.py does not expose missing_guard for the sealed test.",
        "expected_behavior": "missing_guard exists and returns True while present() remains unchanged.",
        "expected_behavior_identity": "missing_guard_expected_symbol",
        "expected_behavior_authority": "preexisting_test_assertion",
        "expected_vs_observed_result": "expected_symbol_missing",
        "baseline_reproduction": "missing_guard=0.0",
        "reproduction_command_or_predicate": "pytest tests/test_sample.py::test_missing_guard",
        "reproduction_attempts": (_attempt(),),
        "reproduction_result": "failed",
        "reproduction_output_digest": "repro-output-digest",
        "first_incorrect_transition": "sealed test imports sample -> expected symbol missing",
        "affected_runtime_stage": "sandbox_candidate_design",
        "affected_capability_id": "missing_guard_capability",
        "originating_mission_id": "mission-contract-test",
        "suspected_owner_paths": ("sample.py",),
        "independent_evidence_paths": ("tests/test_sample.py",),
        "allowed_scope": ("sample.py", "tests/test_sample.py"),
        "excluded_scope": ("DELTA-75", "reports/RC4_*"),
        "materiality_reason": "The sealed behavior cannot be validated without binding implementation and test surfaces.",
        "reproducibility_status": "reproduced",
        "environment_digest": "env-digest",
        "state_digest": "state-digest",
        "authority_class": "local_execution_allowed",
        "ambiguity_status": "resolved",
        "observed_at": "2026-07-16T00:00:02+00:00",
    }
    data.update(overrides)
    return data


def _inspection(*, include_affected=True, include_evidence=True, same_path=False):
    files = []
    if include_affected:
        files.append({"path": "sample.py", "sha256": "sample-digest", "byte_count": 32, "symbols": ("present",)})
    if include_evidence:
        evidence_path = "sample.py" if same_path else "tests/test_sample.py"
        files.append({"path": evidence_path, "sha256": "test-digest", "byte_count": 64, "symbols": ("test_missing_guard",)})
    return {
        "inspection_id": "inspection-001",
        "files": tuple(files),
        "file_count": len(files),
        "meaningful": bool(files),
    }


def _controller_and_subgoal(**evidence_overrides):
    record = compile_behavioral_failure_record(_failure_evidence(**evidence_overrides)).record
    assert record is not None
    controller = start_continuous_runtime_controller(session_id="repository-contract-test")
    controller = attach_continuous_mission(controller, "Optimize your runtime.")
    controller = assess_continuous_mission_behavioral_failures(controller, (record,))
    controller = refresh_continuous_mission_frontier(controller)
    controller = select_continuous_mission_subgoal(controller)
    assert controller.continuous_active_subgoal
    return controller, controller.continuous_active_subgoal


def _with_exact_inspection_scope(controller):
    subgoal = {
        **controller.continuous_active_subgoal,
        "source_inspection_scope": (
            "orchestration/runtime/continuous_runtime_controller.py",
            "tests/runtime_gsr/test_repository_behavior_contract.py",
        ),
    }
    return replace(controller, continuous_active_subgoal=subgoal), subgoal


def test_valid_failure_subgoal_and_inspection_create_pcm_supported_contract():
    controller, subgoal = _controller_and_subgoal()

    contract = compile_repository_behavior_contract(controller, subgoal, _inspection())

    assert contract.failure_id
    assert contract.subgoal_id == subgoal["subgoal_id"]
    assert contract.affected_path == "sample.py"
    assert contract.independent_evidence_path == "tests/test_sample.py"
    assert contract.failure_mechanism == "expected_symbol_missing"
    assert contract.local_implementation_eligibility == "locally_implementable_by_existing_pcm"
    assert not contract.validation_errors
    assert contract.contract_digest


def test_missing_affected_path_rejects_contract():
    controller, subgoal = _controller_and_subgoal()

    contract = compile_repository_behavior_contract(controller, subgoal, _inspection(include_affected=False))

    assert contract.local_implementation_eligibility == "missing_repository_evidence"
    assert "missing_affected_path" in contract.validation_errors


def test_uninspected_named_affected_path_rejects_contract():
    controller, subgoal = _controller_and_subgoal(suspected_owner_paths=("missing.py",))

    contract = compile_repository_behavior_contract(controller, subgoal, _inspection())

    assert contract.local_implementation_eligibility == "missing_repository_evidence"
    assert "missing_affected_path" in contract.validation_errors


def test_missing_independent_evidence_path_rejects_contract():
    controller, subgoal = _controller_and_subgoal()

    contract = compile_repository_behavior_contract(controller, subgoal, _inspection(include_evidence=False))

    assert contract.local_implementation_eligibility == "missing_independent_behavior_contract"
    assert "missing_independent_evidence_path" in contract.validation_errors


def test_same_implementation_and_evidence_path_is_rejected_as_non_independent():
    controller, subgoal = _controller_and_subgoal(independent_evidence_paths=("sample.py",))

    contract = compile_repository_behavior_contract(controller, subgoal, _inspection(same_path=True))

    assert contract.local_implementation_eligibility == "missing_independent_behavior_contract"
    assert "implementation_and_evidence_path_not_independent" in contract.validation_errors


def test_missing_expected_or_current_behavior_rejects_before_contract_creation():
    result = compile_behavioral_failure_record(_failure_evidence(expected_behavior=""))

    assert not result.accepted
    assert "expected_behavior" in result.missing_fields


def test_missing_first_incorrect_transition_rejects_before_contract_creation():
    result = compile_behavioral_failure_record(_failure_evidence(first_incorrect_transition=""))

    assert not result.accepted
    assert "first_incorrect_transition" in result.missing_fields


def test_patch_and_candidate_code_in_advisory_are_rejected():
    controller, subgoal = _controller_and_subgoal(expected_vs_observed_result="wrong_value")

    contract = compile_repository_behavior_contract(
        controller,
        subgoal,
        _inspection(),
        advisory_result={"answer": {"failure_mechanism": "wrong_value", "patch_text": "append code"}},
    )

    assert contract.local_implementation_eligibility == "invalid_scope"
    assert "forbidden_candidate_or_patch_content" in contract.validation_errors


def test_broad_activity_only_evidence_does_not_create_contract_source():
    result = compile_behavioral_failure_record(_failure_evidence(source_type="activity_artifact"))

    assert not result.accepted


def test_advisory_output_cannot_override_deterministic_paths():
    controller, subgoal = _controller_and_subgoal()

    contract = compile_repository_behavior_contract(
        controller,
        subgoal,
        _inspection(),
        advisory_result={
            "answer": {
                "affected_path": "other.py",
                "evidence_path": "tests/other.py",
                "failure_mechanism": "expected_symbol_missing",
                "candidate_behavior": "do the thing",
                "expected_observable_change": "pass",
            }
        },
    )

    assert contract.affected_path == "sample.py"
    assert contract.independent_evidence_path == "tests/test_sample.py"
    assert contract.local_implementation_eligibility == "locally_implementable_by_existing_pcm"


def test_invalid_advisory_json_is_retained_as_digest_but_does_not_loop():
    controller, subgoal = _controller_and_subgoal(expected_vs_observed_result="wrong_value")

    contract = compile_repository_behavior_contract(
        controller,
        subgoal,
        _inspection(),
        advisory_result={"model_id": "local", "executed": True, "answer": "not json"},
    )

    assert contract.advisory_model_digest
    assert contract.local_implementation_eligibility == "unresolved_failure_mechanism"


def test_equivalent_evidence_replay_is_inert_duplicate():
    controller, subgoal = _controller_and_subgoal()
    first = compile_repository_behavior_contract(controller, subgoal, _inspection())

    second = compile_repository_behavior_contract(controller, subgoal, _inspection(), existing_contracts=(first,))

    assert second.contract_id == first.contract_id
    assert second.duplicate_of == first.contract_id


def test_changed_evidence_creates_new_contract_version():
    controller, subgoal = _controller_and_subgoal()
    first = compile_repository_behavior_contract(controller, subgoal, _inspection())
    changed = _inspection()
    changed["files"] = (
        {"path": "sample.py", "sha256": "sample-digest-v2", "byte_count": 32, "symbols": ("present",)},
        {"path": "tests/test_sample.py", "sha256": "test-digest", "byte_count": 64, "symbols": ("test_missing_guard",)},
    )

    second = compile_repository_behavior_contract(controller, subgoal, changed, existing_contracts=(first,))

    assert second.contract_id == first.contract_id
    assert second.contract_digest != first.contract_digest
    assert second.version_of == first.contract_id


def test_pcm_unsupported_repair_shape_is_classified_honestly():
    controller, subgoal = _controller_and_subgoal(expected_vs_observed_result="wrong_transition_state")

    contract = compile_repository_behavior_contract(
        controller,
        subgoal,
        _inspection(),
        advisory_result={
            "failure_mechanism": "state_transition_wrong_order",
            "candidate_behavior": "preserve transition order",
            "expected_observable_change": "state order is correct",
        },
    )

    assert contract.local_implementation_eligibility == "locally_implementable_but_pcm_operation_unsupported"


def test_authority_boundary_creates_authority_request_not_insight(tmp_path):
    controller, subgoal = _controller_and_subgoal(authority_class="operator_authority_required")

    updated, execution = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        allow_local_model_execution=False,
    )

    assert execution.disposition == "blocked_by_authority"
    assert updated.continuous_mission_state == "awaiting_operator_authority"
    assert updated.continuous_developmental_insight_requests[-1]["request_kind"] == "tracked_application_authority"


def test_unsupported_contract_enters_observation_not_operator_insight(tmp_path):
    controller, subgoal = _controller_and_subgoal(
        expected_vs_observed_result="wrong_transition_state",
        suspected_owner_paths=("orchestration/runtime/continuous_runtime_controller.py",),
        independent_evidence_paths=("tests/runtime_gsr/test_repository_behavior_contract.py",),
    )
    controller, subgoal = _with_exact_inspection_scope(controller)

    updated, execution = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        local_model_adapter=lambda _payload: {
            "model_id": "local",
            "executed": True,
            "answer": {
                "failure_mechanism": "state_transition_wrong_order",
                "candidate_behavior": "preserve transition order",
                "expected_observable_change": "state order is correct",
            },
            "provider_calls_performed": False,
        },
        allow_local_model_execution=True,
    )

    assert execution.disposition == "locally_implementable_but_pcm_operation_unsupported"
    assert updated.continuous_mission_state == "observing_for_new_weaknesses"
    assert updated.continuous_observation_state["repository_behavior_contract"]["observation_reason"] == "patch_expressiveness_blocker"
    assert not updated.pending_application_decision_id


def test_supported_contract_writes_artifact_without_patch_or_sandbox(tmp_path):
    controller, subgoal = _controller_and_subgoal(
        suspected_owner_paths=("orchestration/runtime/continuous_runtime_controller.py",),
        independent_evidence_paths=("tests/runtime_gsr/test_repository_behavior_contract.py",),
    )
    controller, subgoal = _with_exact_inspection_scope(controller)

    updated, execution = execute_continuous_active_subgoal(
        controller,
        artifact_root=tmp_path,
        repository_root=Path.cwd(),
        allow_local_model_execution=False,
    )

    assert execution.disposition == "locally_implementable_by_existing_pcm"
    assert updated.continuous_mission_state == "grounded_design_eligible"
    result_root = Path(execution.campaign_root)
    assert (result_root / "repository_behavior_contract.json").exists()
    assert (result_root / "repository_bound_candidate_design.json").exists()
    assert not (result_root / "candidate").exists()
    assert updated.pending_application_decision_id == ""
