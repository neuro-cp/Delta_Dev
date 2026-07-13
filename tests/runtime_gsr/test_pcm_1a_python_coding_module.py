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
