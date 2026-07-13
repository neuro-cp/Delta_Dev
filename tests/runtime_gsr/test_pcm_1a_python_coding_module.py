from __future__ import annotations

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
