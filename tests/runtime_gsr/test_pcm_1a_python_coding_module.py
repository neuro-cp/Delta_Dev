from __future__ import annotations

import hashlib
from dataclasses import replace

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _cycle() -> gsr.GovernedObjectiveCycle:
    objective = gsr.make_development_objective("Governed Python coding module contract", sequence=501)
    return gsr.make_governed_objective_cycle(objective, sequence=501)


def _bundle(**overrides):
    cycle = overrides.get("cycle", _cycle())
    manifest = overrides.get("manifest", gsr.make_python_coding_module_manifest())
    capability = overrides.get(
        "capability",
        gsr.make_python_coding_capability_request(
            cycle,
            manifest,
            requested_source_scope=("orchestration/runtime/example.py",),
            request_sequence=502,
        ),
    )
    attachment = overrides.get(
        "attachment",
        gsr.make_python_coding_module_attachment_request(
            manifest,
            capability,
            requested_attachment_sequence=503,
        ),
    )
    authorization = overrides.get(
        "authorization",
        gsr.make_python_coding_module_attachment_authorization(
            attachment,
            issued_sequence=504,
            expiration_sequence=510,
        ),
    )
    return cycle, manifest, capability, attachment, authorization


def _evaluate(**overrides):
    cycle, manifest, capability, attachment, authorization = _bundle(**overrides)
    return gsr.evaluate_python_coding_module_attachment_eligibility(
        cycle,
        manifest,
        capability,
        attachment,
        authorization,
        sequence=overrides.get("sequence", 505),
    )


def _assert_no_actions(result: gsr.PythonCodingModuleAttachmentEligibilityResult) -> None:
    assert result.attachment_performed is False
    assert result.authorization_consumed is False
    assert result.attachment_record_created is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.registry_mutated is False
    assert result.source_inspection_performed is False
    assert result.source_parsed is False
    assert result.diagnosis_performed is False
    assert result.code_generated is False
    assert result.patch_proposed is False
    assert result.test_proposed is False
    assert result.sandbox_handoff_created is False
    assert result.execution_performed is False
    assert result.source_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False


def test_pcm_1a_exact_safe_python_module_is_eligible_for_inert_attachment_only():
    result = _evaluate()

    assert result.accepted is True
    assert result.reason == "valid"
    assert result.eligible_for_inert_attachment is True
    assert result.authorization.consumed is False
    assert result.manifest.loaded is False
    assert result.manifest.activated is False
    _assert_no_actions(result)


def test_pcm_1a_identity_and_authorization_mismatches_fail_closed():
    cycle, manifest, capability, attachment, authorization = _bundle()
    cases = (
        {"capability": replace(capability, objective_cycle_id="wrong-cycle"), "reason": "wrong_cycle"},
        {"attachment": replace(attachment, manifest_identity="wrong-manifest"), "reason": "wrong_manifest"},
        {"attachment": replace(attachment, module_id="wrong-module"), "reason": "wrong_module"},
        {"attachment": replace(attachment, module_version="9.9.9"), "reason": "wrong_module_version"},
        {"attachment": replace(attachment, manifest_version="wrong-version"), "reason": "wrong_manifest_version"},
        {"attachment": replace(attachment, capability_request_id="wrong-capability"), "reason": "wrong_capability_request"},
        {"authorization": replace(authorization, attachment_request_id="wrong-request"), "reason": "wrong_attachment_request"},
        {"authorization": replace(authorization, attachment_authorization_id="wrong-auth"), "reason": "wrong_attachment_authorization"},
        {"authorization": replace(authorization, operator_authority="DELTA_SELF"), "reason": "non_operator_authorization"},
        {"authorization": replace(authorization, consumed=True), "reason": "consumed"},
        {"authorization": replace(authorization, expiration_sequence=504), "reason": "expired"},
    )

    for case in cases:
        reason = case.pop("reason")
        result = _evaluate(cycle=cycle, manifest=manifest, capability=case.get("capability", capability), attachment=case.get("attachment", attachment), authorization=case.get("authorization", authorization))
        assert result.accepted is False
        assert result.reason == reason
        assert result.eligible_for_inert_attachment is False
        _assert_no_actions(result)


def test_pcm_1a_manifest_capability_and_prohibition_failures_close_the_gate():
    cycle, manifest, capability, attachment, authorization = _bundle()
    cases = (
        (replace(manifest, language="JavaScript"), capability, attachment, authorization, "unsupported_language"),
        (replace(manifest, supported_file_types=(".txt",)), capability, attachment, authorization, "unsupported_file_type"),
        (replace(manifest, capability_set=manifest.capability_set + ("unknown_future_power",)), capability, attachment, authorization, "unknown_capability"),
        (replace(manifest, capability_set=manifest.capability_set + ("execute_code",)), capability, attachment, authorization, "unknown_capability"),
        (replace(manifest, capability_set=("*",)), capability, attachment, authorization, "unrestricted_capability"),
        (replace(manifest, prohibited_capability_set=manifest.prohibited_capability_set[:-1]), capability, attachment, authorization, "prohibited_capability_missing"),
        (replace(manifest, direct_execution_prohibited=False), capability, attachment, authorization, "manifest_inconsistent"),
        (replace(manifest, loaded=True), capability, attachment, authorization, "module_already_loaded"),
        (replace(manifest, activated=True), capability, attachment, authorization, "module_already_activated"),
    )

    for bad_manifest, cap, attach, auth, reason in cases:
        result = gsr.evaluate_python_coding_module_attachment_eligibility(cycle, bad_manifest, cap, attach, auth, sequence=505)
        assert result.accepted is False
        assert result.reason == reason
        _assert_no_actions(result)


def test_pcm_1a_capability_escalation_and_authorized_broader_scope_fail_closed():
    cycle, manifest, capability, attachment, authorization = _bundle()
    broader_capability = replace(capability, requested_capability_set=capability.requested_capability_set + ("submit_to_gsr_workflow_future",))
    broader_attachment = gsr.make_python_coding_module_attachment_request(manifest, broader_capability, requested_attachment_sequence=503)
    broader_authorization = gsr.make_python_coding_module_attachment_authorization(broader_attachment, issued_sequence=504, expiration_sequence=510)
    undeclared = gsr.evaluate_python_coding_module_attachment_eligibility(cycle, manifest, broader_capability, broader_attachment, broader_authorization, sequence=505)
    assert undeclared.accepted is False
    assert undeclared.reason == "capability_mismatch"

    extra_auth = replace(authorization, authorized_capability_set=authorization.authorized_capability_set + ("submit_to_gsr_workflow_future",))
    escalated = _evaluate(cycle=cycle, manifest=manifest, capability=capability, attachment=attachment, authorization=extra_auth)
    assert escalated.accepted is False
    assert escalated.reason == "capability_escalation"
    _assert_no_actions(escalated)


def test_pcm_1a_source_scope_metadata_rejects_unsafe_and_write_enabled_scopes():
    cycle, manifest, capability, attachment, authorization = _bundle()
    unsafe_scopes = (
        ("*", "wildcard_scope"),
        ("../escape.py", "unsafe_source_scope"),
        ("C:/outside.py", "unsafe_source_scope"),
        (".git/config", "unsafe_source_scope"),
        (".env", "unsafe_source_scope"),
        ("DELTA-75/secret.py", "unsafe_source_scope"),
        ("data/canonical_memory/store.sqlite", "unsafe_source_scope"),
        ("reports/RC4_FREEZE_READINESS_FINAL.md", "unsafe_source_scope"),
        ("orchestration/runtime/native.bin", "unsafe_source_scope"),
    )
    for scope, reason in unsafe_scopes:
        bad_capability = replace(capability, requested_source_scope=(scope,))
        bad_attachment = gsr.make_python_coding_module_attachment_request(manifest, bad_capability, requested_attachment_sequence=503)
        bad_authorization = gsr.make_python_coding_module_attachment_authorization(bad_attachment, issued_sequence=504, expiration_sequence=510)
        result = gsr.evaluate_python_coding_module_attachment_eligibility(cycle, manifest, bad_capability, bad_attachment, bad_authorization, sequence=505)
        assert result.accepted is False
        assert result.reason == reason
        _assert_no_actions(result)

    write_enabled = replace(capability, live_writes_prohibited=False)
    write_attachment = gsr.make_python_coding_module_attachment_request(manifest, write_enabled, requested_attachment_sequence=503)
    write_authorization = gsr.make_python_coding_module_attachment_authorization(write_attachment, issued_sequence=504, expiration_sequence=510)
    write_result = gsr.evaluate_python_coding_module_attachment_eligibility(cycle, manifest, write_enabled, write_attachment, write_authorization, sequence=505)
    assert write_result.accepted is False
    assert write_result.reason == "unsafe_source_scope"
    _assert_no_actions(write_result)


def test_pcm_1a_authorization_forbidden_action_flags_fail_closed():
    cycle, manifest, capability, attachment, authorization = _bundle()
    cases = (
        replace(authorization, registry_mutated=True),
        replace(authorization, module_loaded=True),
        replace(authorization, module_activated=True),
        replace(authorization, execution_authorized=True),
        replace(authorization, code_generation_authorized=True),
        replace(authorization, source_inspection_authorized=True),
        replace(authorization, patch_proposal_authorized=True),
        replace(authorization, sandbox_handoff_authorized=True),
        replace(authorization, provider_model_authorized=True),
        replace(authorization, memory_write_authorized=True),
        replace(authorization, persistence_authorized=True),
        replace(authorization, scheduler_authorized=True),
        replace(authorization, background_authorized=True),
    )
    for bad_authorization in cases:
        result = _evaluate(cycle=cycle, manifest=manifest, capability=capability, attachment=attachment, authorization=bad_authorization)
        assert result.accepted is False
        assert result.reason in {"registry_mutation_forbidden", "execution_forbidden"}
        _assert_no_actions(result)


def _assert_no_pcm_1b_actions(result: gsr.PythonCodingModuleAttachmentResult) -> None:
    assert result.attachment_performed is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.registry_mutated is False
    assert result.permissions_granted is False
    assert result.source_inspection_performed is False
    assert result.source_parsed is False
    assert result.diagnosis_performed is False
    assert result.code_generated is False
    assert result.patch_proposed is False
    assert result.test_proposed is False
    assert result.sandbox_handoff_created is False
    assert result.execution_performed is False
    assert result.source_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False


def test_pcm_1b_valid_eligibility_creates_one_inert_attachment_record_only():
    eligibility = _evaluate()
    state = gsr.make_python_coding_module_attachment_state()

    result = gsr.create_python_coding_module_inert_attachment_record(state, eligibility, sequence=506)

    assert result.accepted is True
    assert result.reason == "inert_attachment_record_created"
    assert result.attachment_record_created is True
    assert result.authorization_consumed is True
    assert result.consumed_authorization.consumed is True
    assert eligibility.authorization.consumed is False
    assert len(result.state.attachment_records) == 1
    assert result.state.consumed_attachment_authorization_ids == (eligibility.authorization.attachment_authorization_id,)
    assert result.state.attachment_record_ids_by_module[eligibility.manifest.module_id] == (result.attachment_record.attachment_record_id,)
    assert result.attachment_record.attachment_status == "INERT_ATTACHMENT_RECORD"
    assert result.attachment_record.module_loaded is False
    assert result.attachment_record.module_activated is False
    assert result.attachment_record.registry_mutated is False
    assert result.attachment_record.capability_execution_enabled is False
    assert result.state.registry_entries == ()
    assert result.state.live_registry_mutated is False
    _assert_no_pcm_1b_actions(result)


def test_pcm_1b_reuse_consumed_and_denied_eligibility_fail_without_record():
    eligibility = _evaluate()
    state = gsr.make_python_coding_module_attachment_state()
    first = gsr.create_python_coding_module_inert_attachment_record(state, eligibility, sequence=506)
    second = gsr.create_python_coding_module_inert_attachment_record(first.state, eligibility, sequence=506)

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "attachment_authorization_already_consumed"
    assert len(second.state.attachment_records) == 1
    _assert_no_pcm_1b_actions(second)

    consumed_eligibility = replace(eligibility, authorization=first.consumed_authorization)
    consumed = gsr.create_python_coding_module_inert_attachment_record(state, consumed_eligibility, sequence=506)
    assert consumed.accepted is False
    assert consumed.reason == "consumed"
    assert consumed.state.attachment_records == ()

    denied = replace(eligibility, accepted=False, eligible_for_inert_attachment=False)
    denied_result = gsr.create_python_coding_module_inert_attachment_record(state, denied, sequence=506)
    assert denied_result.accepted is False
    assert denied_result.reason == "eligibility_not_accepted"
    assert denied_result.state.attachment_records == ()


def test_pcm_1b_record_survives_serialization_without_activation():
    eligibility = _evaluate()
    state = gsr.make_python_coding_module_attachment_state()
    result = gsr.create_python_coding_module_inert_attachment_record(state, eligibility, sequence=506)

    restored_state = gsr.deserialize(gsr.PythonCodingModuleAttachmentState, gsr.serialize(result.state))
    restored_record = gsr.deserialize(gsr.PythonCodingModuleAttachmentRecord, restored_state.attachment_records[0])

    assert restored_state.consumed_attachment_authorization_ids == (eligibility.authorization.attachment_authorization_id,)
    assert restored_state.live_registry_mutated is False
    assert restored_state.module_loaded is False
    assert restored_state.module_activated is False
    assert restored_record.attachment_record_id == result.attachment_record.attachment_record_id
    assert restored_record.module_loaded is False
    assert restored_record.module_activated is False
    assert restored_record.registry_mutated is False
    assert restored_record.permissions_granted is False


def _pcm_1b_record() -> gsr.PythonCodingModuleAttachmentRecord:
    eligibility = _evaluate()
    state = gsr.make_python_coding_module_attachment_state()
    result = gsr.create_python_coding_module_inert_attachment_record(state, eligibility, sequence=506)
    assert result.accepted is True
    return result.attachment_record


def _inspection_pair(record: gsr.PythonCodingModuleAttachmentRecord, path: str = "sample.py"):
    request = gsr.make_python_source_inspection_request(
        record,
        requested_relative_paths=(path,),
        request_sequence=507,
    )
    authorization = gsr.make_python_source_inspection_authorization(
        request,
        issued_sequence=508,
        expiration_sequence=520,
    )
    return request, authorization


def _assert_no_pcm_1c_actions(result: gsr.PythonSourceInspectionResult) -> None:
    assert result.diagnosis_performed is False
    assert result.code_generated is False
    assert result.patch_proposed is False
    assert result.test_proposed is False
    assert result.sandbox_handoff_created is False
    assert result.execution_performed is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.registry_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False


def test_pcm_1c_exact_inert_attachment_reads_one_temporary_python_file_structurally(tmp_path):
    record = _pcm_1b_record()
    source = "import os\n\nclass Example:\n    pass\n\ndef alpha(x: int):\n    if x:\n        return os.name\n    return 'n/a'\n"
    target = tmp_path / "sample.py"
    target.write_text(source, encoding="utf-8")
    before_bytes = target.read_bytes()
    before_digest = hashlib.sha256(before_bytes).hexdigest()
    request, authorization = _inspection_pair(record)

    result = gsr.inspect_python_source_read_only(record, request, authorization, root=tmp_path, sequence=509)

    assert result.accepted is True
    assert result.reason == "valid"
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.authorization_consumed is True
    assert result.inspection_started is True
    assert result.inspection_completed is True
    assert result.source_read is True
    assert result.ast_parsed is True
    assert result.evidence.exact_paths_inspected == ("sample.py",)
    assert result.evidence.files_requested == 1
    assert result.evidence.files_read == 1
    assert result.evidence.total_bytes_read == len(before_bytes)
    assert result.evidence.per_file_digests["sample.py"] == before_digest
    observation = gsr.deserialize(gsr.PythonSourceStructuralObservation, result.evidence.observations[0])
    assert observation.path == "sample.py"
    assert observation.byte_count == len(before_bytes)
    assert observation.line_count == len(source.splitlines())
    assert observation.source_digest == before_digest
    assert observation.syntax_valid is True
    assert observation.function_count == 1
    assert observation.class_count == 1
    assert observation.import_count == 1
    assert observation.function_names == ("alpha",)
    assert observation.class_names == ("Example",)
    assert observation.imported_module_names == ("os",)
    assert observation.structural_only is True
    assert observation.diagnosis_absent is True
    assert observation.recommendation_absent is True
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before_digest
    _assert_no_pcm_1c_actions(result)

    reuse = gsr.inspect_python_source_read_only(record, request, result.consumed_authorization, root=tmp_path, sequence=510)
    assert reuse.accepted is False
    assert reuse.reason == "consumed"
    assert reuse.authorization_consumed is False


def test_pcm_1c_identity_authority_permission_and_path_failures_read_nothing(tmp_path):
    record = _pcm_1b_record()
    (tmp_path / "sample.py").write_text("x = 1\n", encoding="utf-8")
    request, authorization = _inspection_pair(record)
    cases = (
        (replace(record, attachment_record_id="wrong-record"), request, authorization, "wrong_attachment_record"),
        (replace(record, attachment_status="ACTIVE"), request, authorization, "attachment_not_inert"),
        (replace(record, module_loaded=True), request, authorization, "module_loaded"),
        (replace(record, module_activated=True), request, authorization, "module_activated"),
        (replace(record, capability_execution_enabled=True), request, authorization, "active_capability_present"),
        (replace(record, authorized_capability_set=()), request, authorization, "source_inspection_not_declared"),
        (record, replace(request, inspection_request_id="wrong-request"), authorization, "wrong_request"),
        (record, request, replace(authorization, inspection_authorization_id="wrong-auth"), "wrong_authorization"),
        (record, request, replace(authorization, operator_authority="DELTA_SELF"), "non_operator_authorization"),
        (record, request, replace(authorization, one_shot=False), "not_one_shot"),
        (record, request, replace(authorization, consumed=True), "consumed"),
        (record, request, replace(authorization, expiration_sequence=508), "expired"),
        (record, replace(request, source_execution_requested=True), authorization, "execution_permission_present"),
        (record, replace(request, diagnosis_requested=True), authorization, "diagnosis_permission_present"),
        (record, replace(request, generation_requested=True), authorization, "generation_permission_present"),
        (record, request, replace(authorization, mutation_prohibited=False), "mutation_permission_present"),
    )

    for bad_record, bad_request, bad_authorization, reason in cases:
        result = gsr.inspect_python_source_read_only(bad_record, bad_request, bad_authorization, root=tmp_path, sequence=509)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.source_read is False
        _assert_no_pcm_1c_actions(result)


def test_pcm_1c_scope_limits_and_filesystem_boundaries_fail_before_consumption(tmp_path):
    record = _pcm_1b_record()
    (tmp_path / "sample.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("y = 2\n", encoding="utf-8")
    unsafe_paths = (
        ("*.py", "wildcard_path"),
        ("../escape.py", "path_traversal"),
        ("C:/outside.py", "absolute_path"),
        (".git/config.py", "forbidden_path"),
        ("DELTA-75/secret.py", "forbidden_path"),
        ("reports/RC4_X.py", "forbidden_path"),
        ("sample.txt", "unsupported_file_type"),
        ("missing.py", "file_missing"),
    )
    for path, reason in unsafe_paths:
        request, authorization = _inspection_pair(record, path)
        result = gsr.inspect_python_source_read_only(record, request, authorization, root=tmp_path, sequence=509)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.source_read is False

    too_many = gsr.make_python_source_inspection_request(record, requested_relative_paths=("sample.py", "two.py"), max_file_count=1, request_sequence=507)
    too_many_auth = gsr.make_python_source_inspection_authorization(too_many, issued_sequence=508, expiration_sequence=520)
    too_many_result = gsr.inspect_python_source_read_only(record, too_many, too_many_auth, root=tmp_path, sequence=509)
    assert too_many_result.accepted is False
    assert too_many_result.reason == "file_count_exceeded"

    too_large = gsr.make_python_source_inspection_request(record, requested_relative_paths=("sample.py",), max_total_bytes=1, request_sequence=507)
    too_large_auth = gsr.make_python_source_inspection_authorization(too_large, issued_sequence=508, expiration_sequence=520)
    too_large_result = gsr.inspect_python_source_read_only(record, too_large, too_large_auth, root=tmp_path, sequence=509)
    assert too_large_result.accepted is False
    assert too_large_result.reason == "byte_limit_exceeded"


def test_pcm_1c_syntax_invalid_source_is_structural_evidence_only(tmp_path):
    record = _pcm_1b_record()
    source = "def broken(:\n    pass\n"
    target = tmp_path / "sample.py"
    target.write_text(source, encoding="utf-8")
    request, authorization = _inspection_pair(record)

    result = gsr.inspect_python_source_read_only(record, request, authorization, root=tmp_path, sequence=509)

    assert result.accepted is True
    observation = gsr.deserialize(gsr.PythonSourceStructuralObservation, result.evidence.observations[0])
    assert observation.syntax_valid is False
    assert observation.parse_error_category == "SyntaxError"
    assert observation.diagnosis_absent is True
    assert observation.recommendation_absent is True
    _assert_no_pcm_1c_actions(result)


def _pcm_1c_result(tmp_path, source: str = "def present():\n    return 1\n"):
    record = _pcm_1b_record()
    target = tmp_path / "sample.py"
    target.write_text(source, encoding="utf-8")
    request, authorization = _inspection_pair(record)
    result = gsr.inspect_python_source_read_only(record, request, authorization, root=tmp_path, sequence=509)
    assert result.accepted is True
    return record, result


def _diagnosis_pair(
    record: gsr.PythonCodingModuleAttachmentRecord,
    inspection_result: gsr.PythonSourceInspectionResult,
    *,
    expected_symbol: str = "missing_guard",
    expected_transition: str = "missing_guard_function_present",
):
    request = gsr.make_python_bounded_diagnosis_request(
        record,
        inspection_result,
        diagnosis_question="Does the accepted structural evidence contain the expected guard symbol?",
        expected_transition=expected_transition,
        expected_symbol=expected_symbol,
        expected_symbol_kind="function",
        request_sequence=510,
    )
    authorization = gsr.make_python_bounded_diagnosis_authorization(
        request,
        issued_sequence=511,
        expiration_sequence=530,
    )
    return request, authorization


def _assert_no_pcm_1d_actions(result: gsr.PythonBoundedDiagnosisResult) -> None:
    assert result.source_reread is False
    assert result.source_executed is False
    assert result.source_imported is False
    assert result.code_generated is False
    assert result.patch_proposed is False
    assert result.test_proposed is False
    assert result.sandbox_handoff_created is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.registry_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False


def test_pcm_1d_exact_inspection_evidence_produces_one_bounded_symbol_missing_finding(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path, source="def present():\n    return 1\n")
    request, authorization = _diagnosis_pair(record, inspection_result)

    result = gsr.perform_python_bounded_diagnosis(record, inspection_result, request, authorization, sequence=512)

    assert result.accepted is True
    assert result.reason == "valid"
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.authorization_consumed is True
    assert result.diagnosis_started is True
    assert result.diagnosis_completed is True
    assert result.finding_created is True
    assert result.finding_count == 1
    assert result.evidence.findings_produced == 1
    assert result.evidence.maximum_findings == 1
    assert result.evidence.exact_paths == inspection_result.evidence.exact_paths_inspected
    assert result.evidence.exact_source_digests == inspection_result.evidence.per_file_digests
    assert result.evidence.inspection_attempt_id == inspection_result.evidence.inspection_attempt_id
    assert result.evidence.inspection_evidence_id == request.inspection_evidence_id
    finding = gsr.deserialize(gsr.PythonBoundedDiagnosticFinding, result.evidence.finding)
    assert finding.path == "sample.py"
    assert finding.source_digest == inspection_result.evidence.per_file_digests["sample.py"]
    assert finding.diagnosis_category == "expected_symbol_missing"
    assert finding.expected_transition == request.expected_transition
    assert "function_names" in finding.observed_structural_evidence
    assert finding.first_incorrect_or_missing_transition == "expected_function_missing_guard_absent_from_structural_observation"
    assert finding.responsible_symbol == "missing_guard"
    assert finding.responsible_structural_location == "sample.py:module_structure"
    assert finding.bounded_impact
    assert finding.confidence > 0
    assert finding.uncertainty
    assert finding.recommendation_absent is True
    assert finding.code_absent is True
    assert finding.patch_absent is True
    assert finding.test_proposal_absent is True
    _assert_no_pcm_1d_actions(result)

    reuse = gsr.perform_python_bounded_diagnosis(record, inspection_result, request, result.consumed_authorization, sequence=513)
    assert reuse.accepted is False
    assert reuse.reason == "consumed"
    assert reuse.authorization_consumed is False


def test_pcm_1d_zero_finding_is_bounded_and_consumes_without_fallback(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path, source="def present():\n    return 1\n")
    request, authorization = _diagnosis_pair(record, inspection_result, expected_symbol="present")

    result = gsr.perform_python_bounded_diagnosis(record, inspection_result, request, authorization, sequence=512)

    assert result.accepted is True
    assert result.reason == "no_bounded_finding"
    assert result.authorization_consumed is True
    assert result.finding_created is False
    assert result.finding_count == 0
    assert result.evidence.finding is None
    assert result.evidence.findings_produced == 0
    _assert_no_pcm_1d_actions(result)


def test_pcm_1d_identity_and_evidence_mismatches_fail_before_diagnosis(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path)
    request, authorization = _diagnosis_pair(record, inspection_result)
    cases = (
        (replace(record, attachment_record_id="wrong-record"), inspection_result, request, authorization, "wrong_attachment_record"),
        (replace(record, attachment_status="ACTIVE"), inspection_result, request, authorization, "attachment_not_inert"),
        (replace(record, module_loaded=True), inspection_result, request, authorization, "module_loaded"),
        (replace(record, module_activated=True), inspection_result, request, authorization, "module_activated"),
        (replace(record, capability_execution_enabled=True), inspection_result, request, authorization, "active_capability_present"),
        (record, replace(inspection_result, accepted=False), request, authorization, "inspection_not_accepted"),
        (record, replace(inspection_result, inspection_completed=False), request, authorization, "inspection_not_completed"),
        (record, inspection_result, replace(request, inspection_request_id="wrong-inspection-request"), authorization, "wrong_inspection_request"),
        (record, inspection_result, replace(request, inspection_attempt_id="wrong-attempt"), authorization, "wrong_inspection_attempt"),
        (record, inspection_result, replace(request, inspection_evidence_id="wrong-evidence"), authorization, "wrong_inspection_evidence"),
        (record, inspection_result, replace(request, exact_inspected_paths=("other.py",)), authorization, "path_mismatch"),
        (record, inspection_result, replace(request, exact_source_digests={"sample.py": "bad"}), authorization, "source_digest_mismatch"),
        (record, inspection_result, replace(request, exact_observation_identities=("bad",)), authorization, "observation_mismatch"),
        (record, inspection_result, replace(request, diagnosis_request_id="wrong-diagnosis-request"), authorization, "wrong_diagnosis_request"),
        (record, inspection_result, request, replace(authorization, diagnosis_authorization_id="wrong-auth"), "wrong_diagnosis_authorization"),
    )

    for bad_record, bad_inspection, bad_request, bad_authorization, reason in cases:
        result = gsr.perform_python_bounded_diagnosis(bad_record, bad_inspection, bad_request, bad_authorization, sequence=512)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.diagnosis_started is False
        _assert_no_pcm_1d_actions(result)


def test_pcm_1d_authority_limits_and_permissions_fail_closed(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path)
    request, authorization = _diagnosis_pair(record, inspection_result)
    cases = (
        (request, replace(authorization, operator_authority="DELTA_SELF"), "non_operator_authorization"),
        (request, replace(authorization, one_shot=False), "not_one_shot"),
        (request, replace(authorization, consumed=True), "consumed"),
        (request, replace(authorization, expiration_sequence=511), "expired"),
        (replace(request, diagnosis_question="different question"), authorization, "diagnosis_question_mismatch"),
        (replace(request, expected_transition="different transition"), authorization, "expected_transition_mismatch"),
        (replace(request, maximum_finding_count=2), authorization, "finding_limit_invalid"),
        (request, replace(authorization, code_generation_prohibited=False), "code_generation_permission_present"),
        (request, replace(authorization, patch_proposal_prohibited=False), "patch_proposal_permission_present"),
        (request, replace(authorization, test_proposal_prohibited=False), "test_proposal_permission_present"),
        (request, replace(authorization, execution_prohibited=False), "execution_permission_present"),
        (request, replace(authorization, mutation_prohibited=False), "mutation_permission_present"),
        (request, replace(authorization, provider_model_use_prohibited=False), "provider_or_model_permission_present"),
        (replace(request, diagnosis_category="broad_review"), authorization, "unsupported_diagnosis_category"),
        (replace(request, expected_symbol=""), authorization, "insufficient_structural_evidence"),
    )

    for bad_request, bad_authorization, reason in cases:
        result = gsr.perform_python_bounded_diagnosis(record, inspection_result, bad_request, bad_authorization, sequence=512)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.diagnosis_started is False
        _assert_no_pcm_1d_actions(result)


def _pcm_1d_result(tmp_path, *, expected_symbol: str = "missing_guard"):
    record, inspection_result = _pcm_1c_result(tmp_path, source="def present():\n    return 1\n")
    request, authorization = _diagnosis_pair(record, inspection_result, expected_symbol=expected_symbol)
    result = gsr.perform_python_bounded_diagnosis(record, inspection_result, request, authorization, sequence=512)
    assert result.accepted is True
    return record, result


def _test_proposal_pair(
    record: gsr.PythonCodingModuleAttachmentRecord,
    diagnosis_result: gsr.PythonBoundedDiagnosisResult,
    *,
    expected_behavior: str = "missing_guard is structurally represented as a function",
):
    request = gsr.make_python_focused_test_proposal_request(
        record,
        diagnosis_result,
        expected_behavior=expected_behavior,
        proposed_test_target_path="tests/runtime_gsr/test_pcm_generated_review.py",
        request_sequence=514,
    )
    authorization = gsr.make_python_focused_test_proposal_authorization(
        request,
        issued_sequence=515,
        expiration_sequence=540,
    )
    return request, authorization


def _assert_no_pcm_1e_actions(result: gsr.PythonFocusedTestProposalResult) -> None:
    assert result.source_reread is False
    assert result.source_patch_created is False
    assert result.test_file_written is False
    assert result.command_executed is False
    assert result.sandbox_handoff_created is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.registry_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False


def test_pcm_1e_exact_diagnosis_produces_one_inert_focused_test_proposal(tmp_path):
    record, diagnosis_result = _pcm_1d_result(tmp_path)
    request, authorization = _test_proposal_pair(record, diagnosis_result)

    result = gsr.create_python_focused_test_proposal(record, diagnosis_result, request, authorization, sequence=516)

    assert result.accepted is True
    assert result.reason == "valid"
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.authorization_consumed is True
    assert result.proposal_started is True
    assert result.proposal_completed is True
    assert result.proposal_created is True
    assert result.proposal_count == 1
    assert result.evidence.proposals_produced == 1
    assert result.evidence.maximum_proposals == 1
    assert result.evidence.diagnosis_attempt_id == diagnosis_result.evidence.diagnosis_attempt_id
    assert result.evidence.diagnosis_evidence_id == request.diagnosis_evidence_id
    assert result.evidence.finding_id == request.finding_id
    assert result.evidence.exact_source_path == request.source_path
    assert result.evidence.exact_source_digest == request.source_digest
    proposal = gsr.deserialize(gsr.PythonFocusedTestProposal, result.evidence.proposal)
    assert proposal.finding_id == request.finding_id
    assert proposal.source_path == "sample.py"
    assert proposal.source_digest == request.source_digest
    assert proposal.responsible_symbol == "missing_guard"
    assert proposal.expected_behavior == request.expected_behavior
    assert proposal.proposed_test_name == "test_missing_guard_expected_symbol_present"
    assert proposal.proposed_test_target_path == "tests/runtime_gsr/test_pcm_generated_review.py"
    assert "missing_guard" in proposal.proposed_test_body
    assert proposal.fixture_requirements == ("accepted PCM-1C structural observation fixture",)
    assert proposal.expected_assertion == "'missing_guard' appears in function_names"
    assert proposal.expected_pre_fix_result.startswith("fails")
    assert proposal.expected_post_fix_result.startswith("passes")
    assert proposal.production_patch_absent is True
    assert proposal.replacement_production_code_absent is True
    assert proposal.shell_commands_absent is True
    assert proposal.git_instructions_absent is True
    assert proposal.automatic_execution_permission_absent is True
    _assert_no_pcm_1e_actions(result)

    reuse = gsr.create_python_focused_test_proposal(record, diagnosis_result, request, result.consumed_authorization, sequence=517)
    assert reuse.accepted is False
    assert reuse.reason == "consumed"
    assert reuse.authorization_consumed is False


def test_pcm_1e_zero_proposal_remains_bounded_without_broadening(tmp_path):
    record, diagnosis_result = _pcm_1d_result(tmp_path, expected_symbol="present")
    request, authorization = _test_proposal_pair(record, diagnosis_result)

    result = gsr.create_python_focused_test_proposal(record, diagnosis_result, request, authorization, sequence=516)

    assert result.accepted is True
    assert result.reason == "no_bounded_test_proposal"
    assert result.authorization_consumed is True
    assert result.proposal_created is False
    assert result.proposal_count == 0
    assert result.evidence.proposal is None
    assert result.evidence.proposals_produced == 0
    _assert_no_pcm_1e_actions(result)


def test_pcm_1e_identity_and_evidence_mismatches_fail_before_proposal(tmp_path):
    record, diagnosis_result = _pcm_1d_result(tmp_path)
    request, authorization = _test_proposal_pair(record, diagnosis_result)
    cases = (
        (replace(record, attachment_record_id="wrong-record"), diagnosis_result, request, authorization, "wrong_attachment_record"),
        (replace(record, attachment_status="ACTIVE"), diagnosis_result, request, authorization, "attachment_not_inert"),
        (replace(record, module_loaded=True), diagnosis_result, request, authorization, "module_loaded"),
        (replace(record, module_activated=True), diagnosis_result, request, authorization, "module_activated"),
        (replace(record, capability_execution_enabled=True), diagnosis_result, request, authorization, "active_capability_present"),
        (record, replace(diagnosis_result, accepted=False), request, authorization, "diagnosis_not_accepted"),
        (record, replace(diagnosis_result, diagnosis_completed=False), request, authorization, "diagnosis_not_completed"),
        (record, diagnosis_result, replace(request, diagnosis_attempt_id="wrong-attempt"), authorization, "wrong_diagnosis_attempt"),
        (record, diagnosis_result, replace(request, diagnosis_evidence_id="wrong-evidence"), authorization, "wrong_diagnosis_evidence"),
        (record, diagnosis_result, replace(request, finding_id="wrong-finding"), authorization, "wrong_finding"),
        (record, diagnosis_result, replace(request, source_path="other.py"), authorization, "path_mismatch"),
        (record, diagnosis_result, replace(request, source_digest="bad"), authorization, "source_digest_mismatch"),
        (record, diagnosis_result, replace(request, expected_behavior="different behavior"), authorization, "expected_behavior_mismatch"),
        (record, diagnosis_result, replace(request, proposed_test_target_path="other_test.py"), authorization, "test_target_mismatch"),
        (record, diagnosis_result, replace(request, test_proposal_request_id="wrong-request"), authorization, "wrong_test_proposal_request"),
        (record, diagnosis_result, request, replace(authorization, test_proposal_authorization_id="wrong-auth"), "wrong_test_proposal_authorization"),
    )

    for bad_record, bad_diagnosis, bad_request, bad_authorization, reason in cases:
        result = gsr.create_python_focused_test_proposal(bad_record, bad_diagnosis, bad_request, bad_authorization, sequence=516)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.proposal_started is False
        _assert_no_pcm_1e_actions(result)


def test_pcm_1e_authority_limits_and_permissions_fail_closed(tmp_path):
    record, diagnosis_result = _pcm_1d_result(tmp_path)
    request, authorization = _test_proposal_pair(record, diagnosis_result)
    cases = (
        (request, replace(authorization, operator_authority="DELTA_SELF"), "non_operator_authorization"),
        (request, replace(authorization, one_shot=False), "not_one_shot"),
        (request, replace(authorization, consumed=True), "consumed"),
        (request, replace(authorization, expiration_sequence=515), "expired"),
        (replace(request, maximum_proposal_count=2), authorization, "proposal_limit_invalid"),
        (replace(request, proposal_only=False), authorization, "wrong_test_proposal_request"),
        (replace(request, source_patch_requested=True), authorization, "source_patch_permission_present"),
        (replace(request, test_file_write_requested=True), authorization, "test_file_write_permission_present"),
        (replace(request, execution_requested=True), authorization, "execution_permission_present"),
        (replace(request, mutation_requested=True), authorization, "mutation_permission_present"),
        (replace(request, provider_model_requested=True), authorization, "provider_or_model_permission_present"),
        (request, replace(authorization, source_patch_prohibited=False), "source_patch_permission_present"),
        (request, replace(authorization, test_file_write_prohibited=False), "test_file_write_permission_present"),
        (request, replace(authorization, execution_prohibited=False), "execution_permission_present"),
        (request, replace(authorization, mutation_prohibited=False), "mutation_permission_present"),
        (request, replace(authorization, provider_model_use_prohibited=False), "provider_or_model_permission_present"),
    )

    for bad_request, bad_authorization, reason in cases:
        result = gsr.create_python_focused_test_proposal(record, diagnosis_result, bad_request, bad_authorization, sequence=516)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.proposal_started is False
        _assert_no_pcm_1e_actions(result)


def _pcm_1e_result(tmp_path, *, expected_symbol: str = "missing_guard"):
    record, diagnosis_result = _pcm_1d_result(tmp_path, expected_symbol=expected_symbol)
    request, authorization = _test_proposal_pair(record, diagnosis_result)
    result = gsr.create_python_focused_test_proposal(record, diagnosis_result, request, authorization, sequence=516)
    assert result.accepted is True
    return record, diagnosis_result, result


def _handoff_pair(
    record: gsr.PythonCodingModuleAttachmentRecord,
    inspection_result: gsr.PythonSourceInspectionResult,
    diagnosis_result: gsr.PythonBoundedDiagnosisResult,
    test_proposal_result: gsr.PythonFocusedTestProposalResult,
):
    request = gsr.make_python_sandbox_handoff_request(
        record,
        inspection_result,
        diagnosis_result,
        test_proposal_result,
        allowed_target_paths=("sample.py", "tests/runtime_gsr/test_pcm_generated_review.py"),
        request_sequence=518,
    )
    authorization = gsr.make_python_sandbox_handoff_authorization(
        request,
        issued_sequence=519,
        expiration_sequence=550,
    )
    return request, authorization


def _assert_no_pcm_1f_actions(result: gsr.PythonSandboxHandoffResult) -> None:
    assert result.sandbox_executed is False
    assert result.patch_applied is False
    assert result.source_written is False
    assert result.test_file_written is False
    assert result.command_executed is False
    assert result.git_operation_performed is False
    assert result.source_mutated is False
    assert result.module_loaded is False
    assert result.module_activated is False
    assert result.registry_mutated is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.memory_written is False
    assert result.persistence_performed is False
    assert result.scheduler_started is False
    assert result.thread_started is False
    assert result.background_task_started is False
    assert result.lifecycle_transition_applied is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False


def test_pcm_1f_exact_upstream_evidence_produces_one_inert_sandbox_handoff(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path, source="def present():\n    return 1\n")
    diagnosis_request, diagnosis_authorization = _diagnosis_pair(record, inspection_result)
    diagnosis_result = gsr.perform_python_bounded_diagnosis(record, inspection_result, diagnosis_request, diagnosis_authorization, sequence=512)
    proposal_request, proposal_authorization = _test_proposal_pair(record, diagnosis_result)
    proposal_result = gsr.create_python_focused_test_proposal(record, diagnosis_result, proposal_request, proposal_authorization, sequence=516)
    request, authorization = _handoff_pair(record, inspection_result, diagnosis_result, proposal_result)

    result = gsr.create_python_sandbox_handoff_package(record, inspection_result, diagnosis_result, proposal_result, request, authorization, sequence=520)

    assert result.accepted is True
    assert result.reason == "valid"
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.authorization_consumed is True
    assert result.handoff_created is True
    assert result.handoff_count == 1
    assert result.evidence.handoffs_produced == 1
    assert result.evidence.maximum_handoffs == 1
    assert result.evidence.inspection_evidence_id == request.inspection_evidence_id
    assert result.evidence.diagnosis_evidence_id == request.diagnosis_evidence_id
    assert result.evidence.test_proposal_evidence_id == request.test_proposal_evidence_id
    package = gsr.deserialize(gsr.PythonSandboxHandoffPackage, result.evidence.handoff_package)
    assert package.attachment_record_id == record.attachment_record_id
    assert package.finding_id == request.finding_id
    assert package.proposal_id == request.proposal_id
    assert package.source_path == "sample.py"
    assert package.source_digest == request.source_digest
    assert package.proposed_test_target_path == "tests/runtime_gsr/test_pcm_generated_review.py"
    assert package.expected_behavior == request.expected_behavior
    assert package.execution_prohibited is True
    assert package.application_prohibited is True
    assert package.git_prohibited is True
    assert package.next_required_authorization_type == "gsr_sandbox_plan_review_authorization"
    _assert_no_pcm_1f_actions(result)

    reuse = gsr.create_python_sandbox_handoff_package(record, inspection_result, diagnosis_result, proposal_result, request, result.consumed_authorization, sequence=521)
    assert reuse.accepted is False
    assert reuse.reason == "consumed"
    assert reuse.authorization_consumed is False


def test_pcm_1f_zero_handoff_remains_bounded(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path, source="def present():\n    return 1\n")
    diagnosis_request, diagnosis_authorization = _diagnosis_pair(record, inspection_result, expected_symbol="present")
    diagnosis_result = gsr.perform_python_bounded_diagnosis(record, inspection_result, diagnosis_request, diagnosis_authorization, sequence=512)
    proposal_request, proposal_authorization = _test_proposal_pair(record, diagnosis_result)
    proposal_result = gsr.create_python_focused_test_proposal(record, diagnosis_result, proposal_request, proposal_authorization, sequence=516)
    request, authorization = _handoff_pair(record, inspection_result, diagnosis_result, proposal_result)

    result = gsr.create_python_sandbox_handoff_package(record, inspection_result, diagnosis_result, proposal_result, request, authorization, sequence=520)

    assert result.accepted is True
    assert result.reason == "no_bounded_sandbox_handoff"
    assert result.authorization_consumed is True
    assert result.handoff_created is False
    assert result.handoff_count == 0
    assert result.evidence.handoff_package is None
    _assert_no_pcm_1f_actions(result)


def test_pcm_1f_upstream_identity_mismatches_fail_before_handoff(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path)
    diagnosis_request, diagnosis_authorization = _diagnosis_pair(record, inspection_result)
    diagnosis_result = gsr.perform_python_bounded_diagnosis(record, inspection_result, diagnosis_request, diagnosis_authorization, sequence=512)
    proposal_request, proposal_authorization = _test_proposal_pair(record, diagnosis_result)
    proposal_result = gsr.create_python_focused_test_proposal(record, diagnosis_result, proposal_request, proposal_authorization, sequence=516)
    request, authorization = _handoff_pair(record, inspection_result, diagnosis_result, proposal_result)
    cases = (
        (replace(record, attachment_record_id="wrong-record"), inspection_result, diagnosis_result, proposal_result, request, authorization, "wrong_attachment_record"),
        (replace(record, attachment_status="ACTIVE"), inspection_result, diagnosis_result, proposal_result, request, authorization, "attachment_not_inert"),
        (replace(record, module_loaded=True), inspection_result, diagnosis_result, proposal_result, request, authorization, "module_loaded"),
        (replace(record, module_activated=True), inspection_result, diagnosis_result, proposal_result, request, authorization, "module_activated"),
        (replace(record, capability_execution_enabled=True), inspection_result, diagnosis_result, proposal_result, request, authorization, "active_capability_present"),
        (record, replace(inspection_result, accepted=False), diagnosis_result, proposal_result, request, authorization, "inspection_not_accepted"),
        (record, inspection_result, replace(diagnosis_result, accepted=False), proposal_result, request, authorization, "diagnosis_not_accepted"),
        (record, inspection_result, diagnosis_result, replace(proposal_result, accepted=False), request, authorization, "test_proposal_not_accepted"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(request, inspection_evidence_id="wrong-inspection-evidence"), authorization, "wrong_inspection_evidence"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(request, diagnosis_evidence_id="wrong-diagnosis-evidence"), authorization, "wrong_diagnosis_evidence"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(request, test_proposal_evidence_id="wrong-proposal-evidence"), authorization, "wrong_test_proposal_evidence"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(request, finding_id="wrong-finding"), authorization, "wrong_finding"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(request, proposal_id="wrong-proposal"), authorization, "wrong_test_proposal"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(request, source_path="other.py"), authorization, "path_mismatch"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(request, source_digest="bad"), authorization, "source_digest_mismatch"),
    )

    for bad_record, bad_inspection, bad_diagnosis, bad_proposal, bad_request, bad_authorization, reason in cases:
        result = gsr.create_python_sandbox_handoff_package(bad_record, bad_inspection, bad_diagnosis, bad_proposal, bad_request, bad_authorization, sequence=520)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.handoff_started is False
        _assert_no_pcm_1f_actions(result)


def test_pcm_1f_authority_limits_and_permissions_fail_closed(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path)
    diagnosis_request, diagnosis_authorization = _diagnosis_pair(record, inspection_result)
    diagnosis_result = gsr.perform_python_bounded_diagnosis(record, inspection_result, diagnosis_request, diagnosis_authorization, sequence=512)
    proposal_request, proposal_authorization = _test_proposal_pair(record, diagnosis_result)
    proposal_result = gsr.create_python_focused_test_proposal(record, diagnosis_result, proposal_request, proposal_authorization, sequence=516)
    request, authorization = _handoff_pair(record, inspection_result, diagnosis_result, proposal_result)
    cases = (
        (request, replace(authorization, operator_authority="DELTA_SELF"), "non_operator_authorization"),
        (request, replace(authorization, one_shot=False), "not_one_shot"),
        (request, replace(authorization, consumed=True), "consumed"),
        (request, replace(authorization, expiration_sequence=519), "expired"),
        (replace(request, maximum_handoff_count=2), authorization, "handoff_limit_invalid"),
        (replace(request, handoff_only=False), authorization, "wrong_sandbox_handoff_request"),
        (replace(request, sandbox_execution_requested=True), authorization, "sandbox_execution_permission_present"),
        (replace(request, patch_application_requested=True), authorization, "patch_application_permission_present"),
        (replace(request, source_write_requested=True), authorization, "source_write_permission_present"),
        (replace(request, test_file_write_requested=True), authorization, "test_file_write_permission_present"),
        (replace(request, git_operation_requested=True), authorization, "git_permission_present"),
        (replace(request, mutation_requested=True), authorization, "mutation_permission_present"),
        (replace(request, provider_model_requested=True), authorization, "provider_or_model_permission_present"),
        (request, replace(authorization, sandbox_execution_prohibited=False), "sandbox_execution_permission_present"),
        (request, replace(authorization, patch_application_prohibited=False), "patch_application_permission_present"),
        (request, replace(authorization, source_write_prohibited=False), "source_write_permission_present"),
        (request, replace(authorization, test_file_write_prohibited=False), "test_file_write_permission_present"),
        (request, replace(authorization, git_operation_prohibited=False), "git_permission_present"),
        (request, replace(authorization, mutation_prohibited=False), "mutation_permission_present"),
        (request, replace(authorization, provider_model_use_prohibited=False), "provider_or_model_permission_present"),
    )

    for bad_request, bad_authorization, reason in cases:
        result = gsr.create_python_sandbox_handoff_package(record, inspection_result, diagnosis_result, proposal_result, bad_request, bad_authorization, sequence=520)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.handoff_started is False
        _assert_no_pcm_1f_actions(result)


def _pcm_1f_result(tmp_path):
    record, inspection_result = _pcm_1c_result(tmp_path, source="def present():\n    return 1\n")
    diagnosis_request, diagnosis_authorization = _diagnosis_pair(record, inspection_result)
    diagnosis_result = gsr.perform_python_bounded_diagnosis(record, inspection_result, diagnosis_request, diagnosis_authorization, sequence=512)
    proposal_request, proposal_authorization = _test_proposal_pair(record, diagnosis_result)
    proposal_result = gsr.create_python_focused_test_proposal(record, diagnosis_result, proposal_request, proposal_authorization, sequence=516)
    handoff_request, handoff_authorization = _handoff_pair(record, inspection_result, diagnosis_result, proposal_result)
    handoff_result = gsr.create_python_sandbox_handoff_package(record, inspection_result, diagnosis_result, proposal_result, handoff_request, handoff_authorization, sequence=520)
    assert handoff_result.accepted is True
    return record, inspection_result, diagnosis_result, proposal_result, handoff_result


def _closure_pair(record, inspection_result, diagnosis_result, proposal_result, handoff_result):
    request = gsr.make_python_coding_module_closure_request(
        record,
        inspection_result,
        diagnosis_result,
        proposal_result,
        handoff_result,
        request_sequence=522,
    )
    authorization = gsr.make_python_coding_module_closure_authorization(
        request,
        issued_sequence=523,
        expiration_sequence=560,
    )
    return request, authorization


def _assert_no_pcm_1_closure_actions(result: gsr.PythonCodingModuleClosureResult) -> None:
    assert result.tracked_source_mutated is False
    assert result.sandbox_executed is False
    assert result.module_activated is False
    assert result.git_operation_performed is False
    assert result.provider_called is False
    assert result.model_invoked is False
    assert result.persistence_performed is False
    assert result.next_request_created is False
    assert result.automatic_continuation is False


def test_pcm_1_closure_exact_chain_accepts_disposable_fixture_pilot(tmp_path):
    record, inspection_result, diagnosis_result, proposal_result, handoff_result = _pcm_1f_result(tmp_path)
    request, authorization = _closure_pair(record, inspection_result, diagnosis_result, proposal_result, handoff_result)

    result = gsr.evaluate_python_coding_module_closure(record, inspection_result, diagnosis_result, proposal_result, handoff_result, request, authorization, sequence=524)

    assert result.accepted is True
    assert result.reason == "accepted_for_pcm_1_closure"
    assert authorization.consumed is False
    assert result.consumed_authorization.consumed is True
    assert result.authorization_consumed is True
    assert result.closure_count == 1
    assert result.evidence.stage_order == gsr.PCM_1_STAGE_ORDER
    assert result.evidence.inspection_evidence_id == request.inspection_evidence_id
    assert result.evidence.diagnosis_evidence_id == request.diagnosis_evidence_id
    assert result.evidence.test_proposal_evidence_id == request.test_proposal_evidence_id
    assert result.evidence.sandbox_handoff_evidence_id == request.sandbox_handoff_evidence_id
    disposition = gsr.deserialize(gsr.PythonCodingModulePilotDisposition, result.evidence.pilot_disposition)
    assert disposition.disposition == "accepted_for_pcm_1_closure"
    assert disposition.pilot_classification == "disposable_fixture_end_to_end_contract_pilot"
    _assert_no_pcm_1_closure_actions(result)

    reuse = gsr.evaluate_python_coding_module_closure(record, inspection_result, diagnosis_result, proposal_result, handoff_result, request, result.consumed_authorization, sequence=525)
    assert reuse.accepted is False
    assert reuse.reason == "consumed"
    assert reuse.authorization_consumed is False


def test_pcm_1_closure_rejects_substituted_stale_and_incomplete_artifacts(tmp_path):
    record, inspection_result, diagnosis_result, proposal_result, handoff_result = _pcm_1f_result(tmp_path)
    request, authorization = _closure_pair(record, inspection_result, diagnosis_result, proposal_result, handoff_result)
    cases = (
        (replace(record, module_loaded=True), inspection_result, diagnosis_result, proposal_result, handoff_result, request, authorization, "rejected_capability_escalation"),
        (record, replace(inspection_result, accepted=False), diagnosis_result, proposal_result, handoff_result, request, authorization, "rejected_incomplete_chain"),
        (record, inspection_result, replace(diagnosis_result, accepted=False), proposal_result, handoff_result, request, authorization, "rejected_incomplete_chain"),
        (record, inspection_result, diagnosis_result, replace(proposal_result, accepted=False), handoff_result, request, authorization, "rejected_incomplete_chain"),
        (record, inspection_result, diagnosis_result, proposal_result, replace(handoff_result, accepted=False), request, authorization, "rejected_incomplete_chain"),
        (record, inspection_result, diagnosis_result, proposal_result, handoff_result, replace(request, source_digest="stale"), authorization, "rejected_stale_evidence"),
        (record, inspection_result, diagnosis_result, proposal_result, handoff_result, replace(request, source_path="other.py"), authorization, "rejected_scope_broadening"),
        (record, inspection_result, diagnosis_result, proposal_result, handoff_result, replace(request, finding_id="wrong"), authorization, "rejected_identity_mismatch"),
        (record, inspection_result, diagnosis_result, proposal_result, handoff_result, replace(request, test_proposal_id="wrong"), authorization, "rejected_identity_mismatch"),
        (record, inspection_result, diagnosis_result, proposal_result, handoff_result, replace(request, handoff_package_id="wrong"), authorization, "rejected_identity_mismatch"),
        (record, inspection_result, diagnosis_result, proposal_result, handoff_result, replace(request, stage_order=gsr.PCM_1_STAGE_ORDER[:-1]), authorization, "rejected_incomplete_chain"),
    )

    for bad_record, bad_inspection, bad_diagnosis, bad_proposal, bad_handoff, bad_request, bad_authorization, reason in cases:
        result = gsr.evaluate_python_coding_module_closure(bad_record, bad_inspection, bad_diagnosis, bad_proposal, bad_handoff, bad_request, bad_authorization, sequence=524)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.closure_started is False
        _assert_no_pcm_1_closure_actions(result)


def test_pcm_1_closure_authority_scope_and_capability_escalation_fail_closed(tmp_path):
    record, inspection_result, diagnosis_result, proposal_result, handoff_result = _pcm_1f_result(tmp_path)
    request, authorization = _closure_pair(record, inspection_result, diagnosis_result, proposal_result, handoff_result)
    cases = (
        (request, replace(authorization, operator_authority="DELTA_SELF"), "non_operator_authorization"),
        (request, replace(authorization, one_shot=False), "not_one_shot"),
        (request, replace(authorization, consumed=True), "consumed"),
        (request, replace(authorization, expiration_sequence=523), "expired"),
        (replace(request, maximum_closure_count=2), authorization, "closure_limit_invalid"),
        (replace(request, closure_only=False), authorization, "wrong_closure_request"),
        (replace(request, module_activation_requested=True), authorization, "rejected_capability_escalation"),
        (replace(request, tracked_source_application_requested=True), authorization, "rejected_scope_broadening"),
        (replace(request, sandbox_execution_requested=True), authorization, "rejected_scope_broadening"),
        (replace(request, git_operation_requested=True), authorization, "rejected_scope_broadening"),
        (replace(request, provider_model_requested=True), authorization, "provider_or_model_permission_present"),
        (replace(request, persistence_requested=True), authorization, "persistence_permission_present"),
        (request, replace(authorization, module_activation_prohibited=False), "rejected_capability_escalation"),
        (request, replace(authorization, tracked_source_application_prohibited=False), "tracked_source_application_permission_present"),
        (request, replace(authorization, sandbox_execution_prohibited=False), "sandbox_execution_permission_present"),
        (request, replace(authorization, git_operation_prohibited=False), "git_permission_present"),
        (request, replace(authorization, provider_model_use_prohibited=False), "provider_or_model_permission_present"),
        (request, replace(authorization, persistence_prohibited=False), "persistence_permission_present"),
    )

    for bad_request, bad_authorization, reason in cases:
        result = gsr.evaluate_python_coding_module_closure(record, inspection_result, diagnosis_result, proposal_result, handoff_result, bad_request, bad_authorization, sequence=524)
        assert result.accepted is False
        assert result.reason == reason
        assert result.authorization_consumed is False
        assert result.closure_started is False
        _assert_no_pcm_1_closure_actions(result)
