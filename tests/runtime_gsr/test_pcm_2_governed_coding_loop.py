from __future__ import annotations

import shutil
import sys
from dataclasses import replace
from pathlib import Path

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _cycle() -> gsr.GovernedObjectiveCycle:
    objective = gsr.make_development_objective("Governed Python coding module contract", sequence=901)
    return gsr.make_governed_objective_cycle(objective, sequence=901)


def _pcm_1_record() -> gsr.PythonCodingModuleAttachmentRecord:
    cycle = _cycle()
    manifest = gsr.make_python_coding_module_manifest()
    capability = gsr.make_python_coding_capability_request(
        cycle,
        manifest,
        requested_source_scope=("sample.py",),
        request_sequence=902,
    )
    attachment = gsr.make_python_coding_module_attachment_request(manifest, capability, requested_attachment_sequence=903)
    authorization = gsr.make_python_coding_module_attachment_authorization(attachment, issued_sequence=904, expiration_sequence=930)
    eligibility = gsr.evaluate_python_coding_module_attachment_eligibility(cycle, manifest, capability, attachment, authorization, sequence=905)
    state = gsr.make_python_coding_module_attachment_state()
    result = gsr.create_python_coding_module_inert_attachment_record(state, eligibility, sequence=906)
    assert result.accepted is True
    assert result.attachment_record is not None
    return result.attachment_record


def _pcm_1_chain(tmp_path: Path, *, source: str = "def present():\n    return 1\n", expected_symbol: str = "missing_guard"):
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    (fixture / "sample.py").write_text(source, encoding="utf-8")
    record = _pcm_1_record()
    inspection_request = gsr.make_python_source_inspection_request(record, requested_relative_paths=("sample.py",), request_sequence=907)
    inspection_authorization = gsr.make_python_source_inspection_authorization(inspection_request, issued_sequence=908, expiration_sequence=930)
    inspection_result = gsr.inspect_python_source_read_only(record, inspection_request, inspection_authorization, root=fixture, sequence=909)
    assert inspection_result.accepted is True

    diagnosis_request = gsr.make_python_bounded_diagnosis_request(
        record,
        inspection_result,
        diagnosis_question=f"Is {expected_symbol} missing?",
        expected_transition=f"{expected_symbol} should appear",
        expected_symbol=expected_symbol,
        request_sequence=910,
    )
    diagnosis_authorization = gsr.make_python_bounded_diagnosis_authorization(diagnosis_request, issued_sequence=911, expiration_sequence=930)
    diagnosis_result = gsr.perform_python_bounded_diagnosis(record, inspection_result, diagnosis_request, diagnosis_authorization, sequence=912)
    assert diagnosis_result.accepted is True
    assert diagnosis_result.evidence.finding is not None

    test_request = gsr.make_python_focused_test_proposal_request(
        record,
        diagnosis_result,
        expected_behavior=f"{expected_symbol} exists",
        proposed_test_target_path="tests/test_pcm_generated_review.py",
        request_sequence=913,
    )
    test_authorization = gsr.make_python_focused_test_proposal_authorization(test_request, issued_sequence=914, expiration_sequence=930)
    test_result = gsr.create_python_focused_test_proposal(record, diagnosis_result, test_request, test_authorization, sequence=915)
    assert test_result.accepted is True
    assert test_result.evidence.proposal is not None

    handoff_request = gsr.make_python_sandbox_handoff_request(
        record,
        inspection_result,
        diagnosis_result,
        test_result,
        allowed_target_paths=("sample.py", "tests/test_pcm_generated_review.py"),
        request_sequence=916,
    )
    handoff_authorization = gsr.make_python_sandbox_handoff_authorization(handoff_request, issued_sequence=917, expiration_sequence=930)
    handoff_result = gsr.create_python_sandbox_handoff_package(record, inspection_result, diagnosis_result, test_result, handoff_request, handoff_authorization, sequence=918)
    assert handoff_result.accepted is True
    return fixture, record, inspection_result, diagnosis_result, test_result, handoff_result


def _patch_result(record, inspection_result, diagnosis_result, test_result, *, replacement_text: str, sequence: int = 919):
    request = gsr.make_python_candidate_patch_request(
        record,
        inspection_result,
        diagnosis_result,
        test_result,
        replacement_text=replacement_text,
        expected_postcondition="symbol_present:missing_guard",
        request_sequence=sequence,
    )
    authorization = gsr.make_python_candidate_patch_authorization(request, issued_sequence=sequence + 1, expiration_sequence=950)
    result = gsr.create_python_candidate_patch_proposal(record, inspection_result, diagnosis_result, test_result, request, authorization, sequence=sequence + 2)
    assert result.accepted is True
    assert result.patch_created is True
    return result


def _artifacts(inspection_result, diagnosis_result, test_result, handoff_result, patch_result, *extra):
    artifacts = (
        ("pcm_1c_read_only_source_inspection", "inspection_evidence", inspection_result.evidence.__dict__),
        ("pcm_1d_bounded_diagnosis", "diagnosis_evidence", diagnosis_result.evidence.__dict__),
        ("pcm_1e_focused_test_proposal", "test_proposal_evidence", test_result.evidence.__dict__),
        ("pcm_1f_sandbox_handoff", "sandbox_handoff_evidence", handoff_result.evidence.__dict__),
        ("pcm_2a_candidate_patch_proposal", "candidate_patch_evidence", patch_result.evidence.__dict__),
    )
    return artifacts + extra


def _materialize(fixture, test_result, patch_result, chain, *, tmp_path: Path, request_sequence: int = 923):
    request = gsr.make_python_sandbox_materialization_request(patch_result, test_result, chain, request_sequence=request_sequence)
    authorization = gsr.make_python_sandbox_materialization_authorization(request, issued_sequence=request_sequence + 1, expiration_sequence=960)
    result = gsr.materialize_python_candidate_in_disposable_sandbox(
        patch_result,
        test_result,
        chain,
        request,
        authorization,
        fixture_root=fixture,
        sandbox_parent=tmp_path,
        sequence=request_sequence + 2,
    )
    assert result.accepted is True
    assert result.manifest is not None
    return result


def _execute(manifest: gsr.PythonSandboxManifest, *, request_sequence: int = 930, timeout_seconds: int = 10, output_byte_limit: int = 4000):
    command = (sys.executable, "-m", "pytest", manifest.test_relative_path)
    request = gsr.make_python_sandbox_execution_request(
        manifest,
        command=command,
        timeout_seconds=timeout_seconds,
        output_byte_limit=output_byte_limit,
        request_sequence=request_sequence,
    )
    authorization = gsr.make_python_sandbox_execution_authorization(request, issued_sequence=request_sequence + 1, expiration_sequence=980)
    result = gsr.execute_python_sandbox_focused_test_once(manifest, request, authorization, sequence=request_sequence + 2)
    assert result.accepted is True
    assert result.command_executed is True
    return result


def _successful_attempt(tmp_path: Path, *, replacement_text: str = "def missing_guard():\n    return True\n"):
    fixture, record, inspection_result, diagnosis_result, test_result, handoff_result = _pcm_1_chain(tmp_path)
    patch_result = _patch_result(record, inspection_result, diagnosis_result, test_result, replacement_text=replacement_text)
    chain = gsr.build_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=_artifacts(inspection_result, diagnosis_result, test_result, handoff_result, patch_result),
    )
    materialization = _materialize(fixture, test_result, patch_result, chain, tmp_path=tmp_path)
    execution = _execute(materialization.manifest)
    evaluation = gsr.evaluate_python_sandbox_result(materialization.manifest, patch_result, test_result, execution, chain, sequence=940)
    assert evaluation.accepted is True
    return fixture, record, inspection_result, diagnosis_result, test_result, handoff_result, patch_result, chain, materialization, execution, evaluation


def test_pcm_2a_candidate_patch_and_2b_integrity_chain_are_inert_and_exact(tmp_path):
    fixture, record, inspection_result, diagnosis_result, test_result, handoff_result = _pcm_1_chain(tmp_path)
    patch_result = _patch_result(record, inspection_result, diagnosis_result, test_result, replacement_text="def missing_guard():\n    return True\n")
    assert patch_result.file_written is False
    assert patch_result.command_executed is False
    assert patch_result.sandbox_materialized is False
    assert patch_result.application_performed is False
    patch = gsr.deserialize(gsr.PythonCandidatePatchProposal, patch_result.evidence.patch_proposal)
    assert patch.max_file_count == 1
    assert len(patch.operations) == 1
    reuse = gsr.create_python_candidate_patch_proposal(
        record,
        inspection_result,
        diagnosis_result,
        test_result,
        patch_result.request,
        patch_result.consumed_authorization,
        sequence=922,
    )
    assert reuse.accepted is False
    assert reuse.reason == "consumed"

    chain = gsr.build_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=_artifacts(inspection_result, diagnosis_result, test_result, handoff_result, patch_result),
    )
    assert chain.accepted is True
    validated = gsr.validate_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=_artifacts(inspection_result, diagnosis_result, test_result, handoff_result, patch_result),
        expected_stage_order=tuple(stage for stage, _kind, _payload in _artifacts(inspection_result, diagnosis_result, test_result, handoff_result, patch_result)),
        expected_final_chain_digest=chain.final_chain_digest,
    )
    assert validated.accepted is True
    tampered_patch_evidence = replace(
        patch_result.evidence,
        patch_proposal={**patch_result.evidence.patch_proposal, "expected_postcondition": "tampered"},
    )
    tampered = gsr.validate_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=_artifacts(inspection_result, diagnosis_result, test_result, handoff_result, replace(patch_result, evidence=tampered_patch_evidence)),
        expected_stage_order=tuple(stage for stage, _kind, _payload in _artifacts(inspection_result, diagnosis_result, test_result, handoff_result, patch_result)),
        expected_final_chain_digest=chain.final_chain_digest,
    )
    assert tampered.accepted is False
    assert tampered.reason == "integrity_mismatch"


def test_pcm_2c_2d_2e_successful_disposable_sandbox_attempt(tmp_path):
    *_, materialization, execution, evaluation = _successful_attempt(tmp_path)
    assert materialization.workspace_created is True
    assert materialization.file_written is True
    assert materialization.active_worktree_mutated is False
    assert execution.evidence.exit_code == 0
    assert execution.evidence.timeout_status == "completed"
    assert execution.evidence.output_truncated is False
    assert evaluation.evaluation.classification == "proposal_passed"
    cleaned, reason = gsr.cleanup_python_disposable_sandbox(materialization.manifest)
    assert cleaned is True
    assert reason == "cleaned"
    assert not Path(materialization.manifest.workspace_root).exists()


def test_pcm_2f_failed_first_attempt_then_one_successful_repair(tmp_path):
    fixture, record, inspection_result, diagnosis_result, test_result, handoff_result = _pcm_1_chain(tmp_path)
    bad_patch_result = _patch_result(record, inspection_result, diagnosis_result, test_result, replacement_text="def wrong_guard():\n    return True\n", sequence=919)
    bad_chain = gsr.build_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=_artifacts(inspection_result, diagnosis_result, test_result, handoff_result, bad_patch_result),
    )
    bad_materialization = _materialize(fixture, test_result, bad_patch_result, bad_chain, tmp_path=tmp_path, request_sequence=923)
    bad_execution = _execute(bad_materialization.manifest, request_sequence=930)
    bad_evaluation = gsr.evaluate_python_sandbox_result(bad_materialization.manifest, bad_patch_result, test_result, bad_execution, bad_chain, sequence=940)
    assert bad_evaluation.evaluation.classification == "proposal_failed_test"

    good_patch_result = _patch_result(record, inspection_result, diagnosis_result, test_result, replacement_text="def missing_guard():\n    return True\n", sequence=941)
    good_chain = gsr.build_pcm2_artifact_chain(
        objective_cycle_id=record.objective_cycle_id,
        module_id=record.module_id,
        module_version=record.module_version,
        artifacts=_artifacts(inspection_result, diagnosis_result, test_result, handoff_result, good_patch_result),
    )
    good_materialization = _materialize(fixture, test_result, good_patch_result, good_chain, tmp_path=tmp_path, request_sequence=945)
    good_execution = _execute(good_materialization.manifest, request_sequence=950)
    good_evaluation = gsr.evaluate_python_sandbox_result(good_materialization.manifest, good_patch_result, test_result, good_execution, good_chain, sequence=960)
    assert good_evaluation.evaluation.classification == "proposal_passed"

    iteration = gsr.create_python_bounded_repair_iteration(
        bad_evaluation.evaluation,
        gsr.deserialize(gsr.PythonCandidatePatchProposal, bad_patch_result.evidence.patch_proposal),
        gsr.deserialize(gsr.PythonCandidatePatchProposal, good_patch_result.evidence.patch_proposal),
        good_evaluation.evaluation,
        sequence=970,
    )
    assert iteration.attempts_used == 2
    assert iteration.stop_reason == "success_after_one_repair"
    assert iteration.maximum_attempts == 2
    denied_third = replace(iteration, attempts_used=3)
    assert denied_third.attempts_used > denied_third.maximum_attempts
    for manifest in (bad_materialization.manifest, good_materialization.manifest):
        cleaned, _reason = gsr.cleanup_python_disposable_sandbox(manifest)
        assert cleaned is True


def test_pcm_2g_review_package_and_closure_are_metadata_only(tmp_path):
    fixture, record, inspection_result, diagnosis_result, test_result, handoff_result, patch_result, chain, materialization, execution, evaluation = _successful_attempt(tmp_path)
    cleaned, _reason = gsr.cleanup_python_disposable_sandbox(materialization.manifest)
    patch = gsr.deserialize(gsr.PythonCandidatePatchProposal, patch_result.evidence.patch_proposal)
    package = gsr.create_python_operator_review_package(
        attachment_record=record,
        inspection_result=inspection_result,
        diagnosis_result=diagnosis_result,
        initial_patch=patch,
        initial_evaluation=evaluation.evaluation,
        final_evaluation=evaluation.evaluation,
        chain=chain,
        cleanup_confirmed=cleaned,
        sequence=980,
    )
    assert package.recommendation == "eligible_for_operator_application_review"
    assert package.application_authorization_created is False
    assert package.tracked_source_mutated is False
    authorization = gsr.make_python_coding_module_v2_closure_authorization(package, issued_sequence=981, expiration_sequence=990)
    closure = gsr.evaluate_python_coding_module_v2_closure(package, authorization, sequence=982)
    assert closure.accepted is True
    assert closure.reason == "accepted_for_pcm_2_closure"
    assert closure.consumed_authorization.consumed is True
    assert closure.application_authorization_created is False
    assert closure.tracked_source_mutated is False
    replay = gsr.evaluate_python_coding_module_v2_closure(package, closure.consumed_authorization, sequence=983)
    assert replay.accepted is False
    assert replay.reason == "rejected_authorization_replay"


def test_pcm_2_adversarial_scope_authorization_command_and_cleanup_boundaries(tmp_path):
    fixture, record, inspection_result, diagnosis_result, test_result, handoff_result, patch_result, chain, materialization, execution, evaluation = _successful_attempt(tmp_path)
    request = gsr.make_python_sandbox_materialization_request(patch_result, test_result, chain, request_sequence=991)
    authorization = gsr.make_python_sandbox_materialization_authorization(request, issued_sequence=992, expiration_sequence=1000)
    for bad_request, reason in (
        (replace(request, target_relative_path="../escape.py"), "target_path_mismatch"),
        (replace(request, allowed_fixture_paths=("*.py", "tests/test_pcm_generated_review.py")), "scope_mismatch"),
        (replace(request, network_requested=True), "network_permission_present"),
        (replace(request, dependency_install_requested=True), "dependency_install_permission_present"),
        (replace(request, git_operation_requested=True), "scope_violation"),
    ):
        result = gsr.materialize_python_candidate_in_disposable_sandbox(
            patch_result,
            test_result,
            chain,
            bad_request,
            authorization,
            fixture_root=fixture,
            sandbox_parent=tmp_path,
            sequence=993,
        )
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False

    command_request = gsr.make_python_sandbox_execution_request(
        materialization.manifest,
        command=("git", "status", materialization.manifest.test_relative_path),
        request_sequence=994,
    )
    command_authorization = gsr.make_python_sandbox_execution_authorization(command_request, issued_sequence=995, expiration_sequence=1000)
    command_result = gsr.execute_python_sandbox_focused_test_once(materialization.manifest, command_request, command_authorization, sequence=996)
    assert command_result.accepted is False
    assert command_result.reason == "command_not_allowlisted"
    assert command_result.authorization_consumed is False

    timeout_request = gsr.make_python_sandbox_execution_request(
        materialization.manifest,
        command=(sys.executable, "-m", "pytest", materialization.manifest.test_relative_path),
        timeout_seconds=0,
        request_sequence=997,
    )
    timeout_authorization = gsr.make_python_sandbox_execution_authorization(timeout_request, issued_sequence=998, expiration_sequence=1000)
    timeout_result = gsr.execute_python_sandbox_focused_test_once(materialization.manifest, timeout_request, timeout_authorization, sequence=999)
    assert timeout_result.accepted is True
    assert timeout_result.authorization_consumed is True
    assert timeout_result.evidence.timeout_status == "timeout"

    closure_auth = gsr.make_python_coding_module_v2_closure_authorization(
        gsr.create_python_operator_review_package(
            attachment_record=record,
            inspection_result=inspection_result,
            diagnosis_result=diagnosis_result,
            initial_patch=gsr.deserialize(gsr.PythonCandidatePatchProposal, patch_result.evidence.patch_proposal),
            initial_evaluation=evaluation.evaluation,
            final_evaluation=evaluation.evaluation,
            chain=chain,
            cleanup_confirmed=False,
            sequence=1001,
        ),
        issued_sequence=1002,
        expiration_sequence=1010,
    )
    bad_package = gsr.create_python_operator_review_package(
        attachment_record=record,
        inspection_result=inspection_result,
        diagnosis_result=diagnosis_result,
        initial_patch=gsr.deserialize(gsr.PythonCandidatePatchProposal, patch_result.evidence.patch_proposal),
        initial_evaluation=evaluation.evaluation,
        final_evaluation=evaluation.evaluation,
        chain=chain,
        cleanup_confirmed=False,
        sequence=1001,
    )
    closure = gsr.evaluate_python_coding_module_v2_closure(bad_package, closure_auth, sequence=1003)
    assert closure.accepted is False
    assert closure.reason == "rejected_cleanup_failure"
    gsr.cleanup_python_disposable_sandbox(materialization.manifest)


def test_pcm_2_temp_workspaces_are_disposable_and_not_repo_tracked(tmp_path):
    *_, materialization, _execution, _evaluation = _successful_attempt(tmp_path)
    workspace = Path(materialization.manifest.workspace_root)
    assert workspace.exists()
    assert workspace.name.startswith("pcm2_sandbox_")
    assert not (workspace / ".git").exists()
    assert not any("DELTA-75" in part for part in workspace.parts)
    cleaned, reason = gsr.cleanup_python_disposable_sandbox(materialization.manifest)
    assert cleaned is True
    assert reason == "cleaned"
    if workspace.exists():
        shutil.rmtree(workspace)
