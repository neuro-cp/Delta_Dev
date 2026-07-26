from orchestration.runtime.cognitive_proposal_pipeline import (
    CallBudget,
    artifact_digest,
    audit_stage1_fixture_integrity,
    audit_stage2_fixture_integrity,
    audit_stage3_allowlist_integrity,
    audit_stage4_fixture_integrity,
    assemble_validated_cognitive_proposal,
    audit_cognitive_proposal_consistency,
    assemble_cognitive_proposal,
    build_stage1_internal_request,
    build_stage2_internal_request,
    build_stage3_internal_request,
    build_stage4_internal_request,
    stage1_model_messages,
    stage1_revision_messages,
    stage2_model_messages,
    stage2_revision_messages,
    stage3_model_messages,
    stage3_revision_messages,
    stage4_model_messages,
    stage4_revision_messages,
    validate_bounded_strategy,
    validate_assembled_cognitive_proposal,
    validate_evidence_selection,
    validate_final_proposal,
    validate_grounded_diagnosis,
    validate_path_selection,
)


IMPL = "orchestration/runtime/autonomy_advisory_assistance.py"
TEST = "tests/runtime_gsr/test_autonomy_18_advisory_assistance.py"
EVIDENCE_KEY = "ck-adapter-fixture:duplicate-replay"
AUTHORITY = {"provider_calls": 0, "network": False, "deployment": False, "credentials": False, "source_mutation": False}


def packet():
    return {
        "problem_id": "p1",
        "sources": [{
            "source_id": "ck-adapter-fixture",
            "excerpt_id": "duplicate-replay",
            "path": IMPL,
            "excerpt": "existing advisory_output.json replay must check report.status and grounding_audit.accepted",
        }],
    }


def stage2_packet():
    return {
        "problem_id": "p2",
        "problem_statement": "Determine why a request did not complete.",
        "sources": [{
            "source_id": "service-log",
            "excerpt_id": "timeout-line",
            "path": "fixture/service.log",
            "excerpt": "The request exceeded the 30-second timeout and was terminated.",
        }],
    }


def evidence_selection():
    return {
        "result_type": "evidence_selection",
        "problem_id": "p1",
        "selected_evidence": [{
            "source_id": "ck-adapter-fixture",
            "excerpt_id": "duplicate-replay",
            "path": IMPL,
            "supported_claim": "duplicate replay must check report status and accepted grounding audit",
        }],
        "missing_claims": [],
        "uncertainty": {"score": 0.2, "reason": "direct excerpt"},
    }


def stage2_evidence_selection():
    return {
        "result_type": "evidence_selection",
        "problem_id": "p2",
        "selected_evidence": [{
            "source_id": "service-log",
            "excerpt_id": "timeout-line",
            "path": "fixture/service.log",
            "supported_claim": "request exceeded timeout and was terminated",
            "text": "The request exceeded the 30-second timeout and was terminated.",
        }],
        "missing_claims": [],
        "uncertainty": {"score": 0.1, "reason": "direct log line"},
    }


def diagnosis():
    return {
        "result_type": "grounded_diagnosis",
        "problem_id": "p1",
        "diagnosis": "Duplicate replay accepts stale or rejected artifacts without both checks.",
        "first_incorrect_transition": "existing output -> replay passed without report and grounding validation",
        "evidence_references": [{
            "source_id": "ck-adapter-fixture",
            "excerpt_id": "duplicate-replay",
            "path": IMPL,
            "claim": "duplicate replay must check report status and accepted grounding audit",
        }],
        "limitations": ["single replay transition"],
        "uncertainty": {"score": 0.2, "reason": "direct excerpt"},
    }


def stage2_diagnosis():
    return {
        "result_type": "grounded_diagnosis",
        "problem_id": "p2",
        "diagnosis": "The request failed because it exceeded the 30-second timeout and was terminated.",
        "first_incorrect_transition": "request exceeded the 30-second timeout -> request was terminated",
        "evidence_references": [{
            "source_id": "service-log",
            "excerpt_id": "timeout-line",
            "path": "fixture/service.log",
            "claim": "request exceeded timeout and was terminated",
        }],
        "limitations": ["single selected evidence record"],
        "uncertainty": {"score": 0.1, "reason": "direct selected evidence"},
    }


def paths():
    return {
        "result_type": "path_selection",
        "problem_id": "p1",
        "implementation_path": IMPL,
        "focused_test_path": TEST,
        "independent_evaluator_path": TEST,
        "selection_reasons": {"implementation": "owns replay branch", "test": "focused A18 evaluator", "evaluator": "existing focused evaluator"},
        "rejected_candidates": [],
        "limitations": ["single bounded path family"],
        "uncertainty": {"score": 0.2, "reason": "allowlisted paths"},
    }


def allowlist():
    return {
        "inspected_implementation_paths": [IMPL],
        "focused_test_paths": [TEST],
        "independent_evaluator_paths": [TEST],
        "permitted_new_test_paths": [],
        "allow_evaluator_as_test": True,
    }


def strategy():
    return {
        "result_type": "bounded_strategy",
        "problem_id": "p1",
        "steps": [{"order": 1, "action": "guard duplicate replay with report and grounding checks", "target_path": IMPL, "purpose": "keep stale rejected artifacts from passing"}],
        "files_allowed": [IMPL],
        "tests_allowed": [TEST],
        "independent_evaluator_path": TEST,
        "expected_behavioral_change": "rejected stale replay returns integrity stop",
        "prohibited_changes": ["do not modify evaluator", "do not claim tests passed"],
        "limitations": ["single replay transition"],
        "uncertainty": {"score": 0.25, "reason": "bounded evidence"},
        "required_authority": ["bounded_local_sandbox"],
        "prohibited_authority": ["provider", "network", "deployment", "credentials", "primary_source_mutation", "source_mutation", "evaluator_mutation", "unrestricted_shell", "unrestricted_execution"],
    }


def abstention():
    return {
        "result_type": "insufficient_evidence",
        "problem_id": "p1",
        "supported_findings": [],
        "missing_evidence": [{"required_clause": "trace", "reason": "missing"}],
        "requested_evidence": ["trace"],
        "limitations": ["no proposal"],
        "uncertainty": {"score": 0.9, "reason": "missing trace"},
    }


def test_stage_1_schema_and_validation_accepts_exact_references():
    result = validate_evidence_selection(evidence_selection(), packet())

    assert result["accepted"] is True
    assert result["abstained"] is False


def test_stage_1_rejects_invented_reference():
    bad = evidence_selection()
    bad["selected_evidence"][0]["excerpt_id"] = "invented"

    result = validate_evidence_selection(bad, packet())

    assert result["accepted"] is False
    assert "invented_evidence_reference" in result["reasons"]


def test_stage_2_grounding_rejects_unsupported_reference_and_missing_uncertainty():
    bad = diagnosis()
    bad["evidence_references"][0]["source_id"] = "invented"
    bad.pop("uncertainty")

    result = validate_grounded_diagnosis(bad, evidence_selection())

    assert result["accepted"] is False
    assert "reference_not_from_stage_1" in result["reasons"]
    assert "uncertainty_required" in result["reasons"]


def test_stage_2_accepts_grounded_diagnosis():
    result = validate_grounded_diagnosis(diagnosis(), evidence_selection())

    assert result["accepted"] is True


def test_stage_2_rejects_wrong_wrapper_and_invented_reference():
    wrapped = {"grounded_diagnosis": {"result_type": "grounded_diagnosis"}}
    invented = stage2_diagnosis()
    invented["evidence_references"][0]["excerpt_id"] = "invented"

    wrapped_result = validate_grounded_diagnosis(wrapped, stage2_evidence_selection())
    invented_result = validate_grounded_diagnosis(invented, stage2_evidence_selection())

    assert wrapped_result["accepted"] is False
    assert "wrong_result_type" in wrapped_result["reasons"]
    assert invented_result["accepted"] is False
    assert "reference_not_from_stage_1" in invented_result["reasons"]


def test_stage_2_rejects_unsupported_diagnosis_missing_uncertainty_and_downstream_planning():
    bad = stage2_diagnosis()
    bad["diagnosis"] = "The operator selected the wrong implementation file."
    bad["first_incorrect_transition"] = "operator approval -> wrong implementation path"
    bad["evidence_references"][0]["claim"] = "wrong implementation path"
    bad.pop("uncertainty")
    bad["implementation_path"] = IMPL

    result = validate_grounded_diagnosis(bad, stage2_evidence_selection())

    assert result["accepted"] is False
    assert "diagnosis_not_supported_by_evidence" in result["reasons"]
    assert "transition_not_supported_by_evidence" in result["reasons"]
    assert "reference_claim_not_supported_by_evidence" in result["reasons"]
    assert "uncertainty_required" in result["reasons"]
    assert "diagnosis_contains_downstream_planning" in result["reasons"]


def test_stage_2_rejects_missing_limitations():
    bad = stage2_diagnosis()
    bad["limitations"] = []

    result = validate_grounded_diagnosis(bad, stage2_evidence_selection())

    assert result["accepted"] is False
    assert "limitations_required" in result["reasons"]


def test_stage_2_clean_messages_do_not_serialize_internal_envelope_or_output_wrapper():
    internal = build_stage2_internal_request(
        request_id="r2",
        model_id="m1",
        problem_id="p2",
        problem_statement=stage2_packet()["problem_statement"],
        evidence_selection=stage2_evidence_selection(),
        evidence_packet=stage2_packet(),
        budget={"maximum": 2},
    )
    user = stage2_model_messages(internal)[1]["content"]

    assert internal["request_id"] == "r2"
    assert "request_id" not in user
    assert "budget" not in user
    assert '"grounded_diagnosis":' not in user
    assert "VALIDATED SELECTED EVIDENCE" in user
    assert "timeout-line" in user
    assert "result_type" in user


def test_stage_2_revision_is_stateless_and_structural_without_answer_leakage():
    internal = build_stage2_internal_request(
        request_id="r2",
        model_id="m1",
        problem_id="p2",
        problem_statement=stage2_packet()["problem_statement"],
        evidence_selection=stage2_evidence_selection(),
        evidence_packet=stage2_packet(),
        budget={"maximum": 2},
    )
    messages = stage2_revision_messages(
        internal_request=internal,
        validation={"reasons": ("wrong_result_type",)},
        response_keys=("validated_evidence_selection",),
    )
    text = messages[1]["content"]

    assert "wrong_result_type" in text
    assert "VALIDATED SELECTED EVIDENCE" in text
    assert "The request failed because it exceeded" not in text
    assert '"grounded_diagnosis":' not in text


def test_stage_2_fixture_integrity_accepts_visible_selected_evidence():
    result = audit_stage2_fixture_integrity(
        evidence_selection=stage2_evidence_selection(),
        evidence_packet=stage2_packet(),
    )

    assert result["accepted"] is True
    assert result["selected_count"] == 1


def test_stage_2_fixture_integrity_rejects_missing_selected_source():
    bad = stage2_evidence_selection()
    bad["selected_evidence"][0]["excerpt_id"] = "missing"

    result = audit_stage2_fixture_integrity(evidence_selection=bad, evidence_packet=stage2_packet())

    assert result["accepted"] is False
    assert "selected_source_missing" in result["reasons"]


def test_stage_3_exact_path_selection_and_independence():
    result = validate_path_selection(paths(), allowlist())

    assert result["accepted"] is True


def test_stage_3_rejects_invented_broad_and_nonindependent_paths():
    bad = paths()
    bad["implementation_path"] = "DELTA-75/*"
    bad["independent_evaluator_path"] = "DELTA-75/*"

    result = validate_path_selection(bad, allowlist())

    assert result["accepted"] is False
    assert "implementation_path_not_inspected" in result["reasons"]
    assert "evaluator_path_not_allowed" in result["reasons"]
    assert "prohibited_or_broad_path" in result["reasons"]


def test_stage_3_rejects_uninspected_wildcard_traversal_and_missing_uncertainty():
    bad = paths()
    bad["implementation_path"] = "orchestration/runtime/*.py"
    bad["focused_test_path"] = "../tests/runtime_gsr/test_autonomy_18_advisory_assistance.py"
    bad.pop("uncertainty")

    result = validate_path_selection(bad, allowlist())

    assert result["accepted"] is False
    assert "implementation_path_not_inspected" in result["reasons"]
    assert "focused_test_path_not_allowed" in result["reasons"]
    assert "prohibited_or_broad_path" in result["reasons"]
    assert "uncertainty_required" in result["reasons"]


def test_stage_3_rejects_evaluator_conflict_when_not_allowed_and_downstream_strategy():
    bad = paths()
    bad["independent_evaluator_path"] = TEST
    bad["bounded_strategy"] = ["patch the file"]
    strict = {**allowlist(), "allow_evaluator_as_test": False}

    result = validate_path_selection(bad, strict)

    assert result["accepted"] is False
    assert "evaluator_not_independent" in result["reasons"]
    assert "path_selection_contains_downstream_strategy" in result["reasons"]


def test_stage_3_rejects_missing_limitations():
    bad = paths()
    bad["limitations"] = []

    result = validate_path_selection(bad, allowlist())

    assert result["accepted"] is False
    assert "limitations_required" in result["reasons"]


def test_stage_3_clean_messages_do_not_serialize_internal_envelope_or_output_wrapper():
    internal = build_stage3_internal_request(
        request_id="r3",
        model_id="m1",
        problem_id="p1",
        problem_statement="Select bounded paths.",
        diagnosis=diagnosis(),
        allowlist=allowlist(),
        budget={"maximum": 2},
    )
    user = stage3_model_messages(internal)[1]["content"]

    assert internal["request_id"] == "r3"
    assert "request_id" not in user
    assert "budget" not in user
    assert '"path_selection":' not in user
    assert "IMPLEMENTATION CANDIDATES" in user
    assert IMPL in user
    assert TEST in user


def test_stage_3_revision_is_stateless_and_has_no_preferred_path_leakage():
    internal = build_stage3_internal_request(
        request_id="r3",
        model_id="m1",
        problem_id="p1",
        problem_statement="Select bounded paths.",
        diagnosis=diagnosis(),
        allowlist=allowlist(),
        budget={"maximum": 2},
    )
    messages = stage3_revision_messages(
        internal_request=internal,
        validation={"reasons": ("implementation_path_not_inspected",)},
        response_keys=("path_selection",),
    )
    text = messages[1]["content"]

    assert "implementation_path_not_inspected" in text
    assert "IMPLEMENTATION CANDIDATES" in text
    assert "select implementation-1" not in text.lower()
    assert '"path_selection":' not in text


def test_stage_3_allowlist_integrity_accepts_frozen_allowlist():
    result = audit_stage3_allowlist_integrity(allowlist())

    assert result["accepted"] is True
    assert result["implementation_count"] == 1
    assert result["focused_test_count"] == 1
    assert result["evaluator_count"] == 1


def test_stage_3_allowlist_integrity_rejects_missing_roles_and_bad_paths():
    bad = {
        "inspected_implementation_paths": ["DELTA-75/*"],
        "focused_test_paths": [],
        "independent_evaluator_paths": [],
        "permitted_new_test_paths": ["../bad.py"],
    }

    result = audit_stage3_allowlist_integrity(bad)

    assert result["accepted"] is False
    assert "no_focused_test_candidates" not in result["reasons"]
    assert "no_independent_evaluator_candidates" in result["reasons"]
    assert "invalid_implementation_path" in result["reasons"]
    assert "invalid_proposed_test_path" in result["reasons"]


def test_stage_4_bounded_strategy_accepts_narrow_scope():
    result = validate_bounded_strategy(strategy(), path_selection=paths())

    assert result["accepted"] is True


def test_stage_4_rejects_evaluator_mutation_and_prohibited_authority():
    bad = strategy()
    bad["files_allowed"] = [IMPL, TEST]
    bad["required_authority"] = ["network"]

    result = validate_bounded_strategy(bad, path_selection=paths())

    assert result["accepted"] is False
    assert "strategy_modifies_evaluator" in result["reasons"]
    assert "prohibited_authority_requested" in result["reasons"]


def test_stage_4_rejects_invented_path_broad_target_success_claim_and_missing_uncertainty():
    bad = strategy()
    bad["files_allowed"] = [IMPL, "orchestration/runtime/invented.py"]
    bad["tests_allowed"] = [TEST, "tests/runtime_gsr/*"]
    bad["steps"][0]["target_path"] = "orchestration/runtime/*"
    bad["expected_behavioral_change"] = "Tests now pass and the defect is fixed."
    bad.pop("uncertainty")

    result = validate_bounded_strategy(bad, path_selection=paths())

    assert result["accepted"] is False
    assert "invented_or_unselected_file_allowed" in result["reasons"]
    assert "invented_or_unselected_test_allowed" in result["reasons"]
    assert "step_target_not_selected" in result["reasons"]
    assert "prohibited_or_broad_path" in result["reasons"]
    assert "success_claim_prohibited" in result["reasons"]
    assert "uncertainty_required" in result["reasons"]


def test_stage_4_rejects_missing_limitations_and_missing_prohibited_authority():
    bad = strategy()
    bad["limitations"] = []
    bad["prohibited_authority"] = ["provider"]

    result = validate_bounded_strategy(bad, path_selection=paths())

    assert result["accepted"] is False
    assert "limitations_required" in result["reasons"]
    assert "prohibited_authority_not_explicit" in result["reasons"]


def test_stage_4_clean_messages_do_not_serialize_internal_envelope_or_output_wrapper():
    internal = build_stage4_internal_request(
        request_id="r4",
        model_id="m1",
        problem_id="p1",
        problem_statement="Plan bounded repair.",
        diagnosis=diagnosis(),
        path_selection=paths(),
        authority={},
        prohibited_changes=("do not modify evaluator",),
        budget={"maximum": 2},
    )
    user = stage4_model_messages(internal)[1]["content"]

    assert internal["request_id"] == "r4"
    assert "request_id" not in user
    assert "budget" not in user
    assert '"bounded_strategy":' not in user
    assert IMPL in user
    assert TEST in user


def test_stage_4_revision_is_stateless_and_has_no_strategy_answer_leakage():
    internal = build_stage4_internal_request(
        request_id="r4",
        model_id="m1",
        problem_id="p1",
        problem_statement="Plan bounded repair.",
        diagnosis=diagnosis(),
        path_selection=paths(),
        authority={},
        prohibited_changes=("do not modify evaluator",),
        budget={"maximum": 2},
    )
    messages = stage4_revision_messages(
        internal_request=internal,
        validation={"reasons": ("success_claim_prohibited",)},
        response_keys=("bounded_strategy",),
    )
    text = messages[1]["content"]

    assert "success_claim_prohibited" in text
    assert "Selected implementation path" in text
    assert "guard duplicate replay" not in text
    assert '"bounded_strategy":' not in text


def test_stage_4_fixture_integrity_accepts_selected_paths():
    result = audit_stage4_fixture_integrity(diagnosis=diagnosis(), path_selection=paths())

    assert result["accepted"] is True


def test_stage_4_fixture_integrity_rejects_missing_transition_and_bad_path():
    bad_diag = diagnosis()
    bad_diag["first_incorrect_transition"] = ""
    bad_paths = paths()
    bad_paths["implementation_path"] = "DELTA-75/*"

    result = audit_stage4_fixture_integrity(diagnosis=bad_diag, path_selection=bad_paths)

    assert result["accepted"] is False
    assert "transition_missing" in result["reasons"]
    assert "implementation_path_invalid" in result["reasons"]


def test_typed_abstention_at_each_stage_stops_safely():
    for validator, extra in (
        (validate_evidence_selection, (packet(),)),
        (validate_grounded_diagnosis, (evidence_selection(),)),
        (validate_path_selection, (allowlist(),)),
    ):
        result = validator(abstention(), *extra)
        assert result["accepted"] is True
        assert result["abstained"] is True


def test_call_budget_enforces_maximum_and_stop_after_abstention():
    budget = CallBudget(2)

    assert budget.consume() is True
    assert budget.consume() is True
    assert budget.consume() is False
    assert budget.to_record() == {"maximum": 2, "used": 2, "remaining": 0}


def test_deterministic_structural_assembly_without_semantic_invention():
    proposal = assemble_cognitive_proposal(problem_id="p1", diagnosis=diagnosis(), path_selection=paths(), strategy=strategy())

    assert proposal["diagnosis"] == diagnosis()["diagnosis"]
    assert proposal["implementation_path"] == IMPL
    assert proposal["evidence_references"] == tuple(diagnosis()["evidence_references"])


def test_final_cognitive_proposal_and_grounding_validation_unchanged():
    proposal = assemble_cognitive_proposal(problem_id="p1", diagnosis=diagnosis(), path_selection=paths(), strategy=strategy())
    result = validate_final_proposal(
        proposal,
        evidence_references=(EVIDENCE_KEY,),
        inspected_paths=(IMPL,),
        evaluator_path=TEST,
        allowed_authority=AUTHORITY,
    )

    assert result["accepted"] is True


def test_missing_field_during_final_assembly_rejects_without_invention():
    incomplete = diagnosis()
    incomplete["evidence_references"] = []
    proposal = assemble_cognitive_proposal(problem_id="p1", diagnosis=incomplete, path_selection=paths(), strategy=strategy())
    result = validate_final_proposal(
        proposal,
        evidence_references=(EVIDENCE_KEY,),
        inspected_paths=(IMPL,),
        evaluator_path=TEST,
        allowed_authority=AUTHORITY,
    )

    assert result["accepted"] is False
    assert "missing_required_cognitive_fields" in result["reasons"]


def _assembled_inputs():
    stage1 = evidence_selection()
    stage1["problem_id"] = "p1"
    stage1["selected_evidence"][0]["text"] = packet()["sources"][0]["excerpt"]
    stage2 = diagnosis()
    stage3 = paths()
    stage4 = strategy()
    digests = {
        "stage1": artifact_digest(stage1),
        "stage2": artifact_digest(stage2),
        "stage3": artifact_digest(stage3),
        "stage4": artifact_digest(stage4),
    }
    proposal = assemble_validated_cognitive_proposal(
        evidence_selection=stage1,
        diagnosis=stage2,
        path_selection=stage3,
        strategy=stage4,
        source_artifact_digests=digests,
    )
    return stage1, stage2, stage3, stage4, proposal


def test_deterministic_validated_proposal_assembly_passes_grounding_without_model_call():
    stage1, stage2, stage3, stage4, proposal = _assembled_inputs()

    result = validate_assembled_cognitive_proposal(
        proposal=proposal,
        evidence_selection=stage1,
        evidence_packet=packet(),
        diagnosis=stage2,
        path_selection=stage3,
        strategy=stage4,
        allowlist=allowlist(),
        allowed_authority=AUTHORITY,
    )

    assert result["accepted"] is True
    assert proposal["assembly_method"] == "deterministic_structural_mapping_v1"
    assert proposal["non_executable"] is True
    assert proposal["execution_disposition"] == "grounded_pending_sandbox_authorization"


def test_duplicate_assembly_uses_same_proposal_identity():
    stage1, stage2, stage3, stage4, proposal = _assembled_inputs()
    digests = proposal["source_stage_artifacts"]

    duplicate = assemble_validated_cognitive_proposal(
        evidence_selection=stage1,
        diagnosis=stage2,
        path_selection=stage3,
        strategy=stage4,
        source_artifact_digests=digests,
    )

    assert duplicate["proposal_id"] == proposal["proposal_id"]


def test_assembled_proposal_negative_controls_reject_bad_cross_stage_content():
    stage1, stage2, stage3, stage4, proposal = _assembled_inputs()
    cases = []
    mixed_stage2 = {**stage2, "problem_id": "other-problem"}
    cases.append((proposal, stage1, mixed_stage2, stage3, stage4, "problem_id_mismatch"))
    no_evidence = {**proposal, "evidence_references": []}
    cases.append((no_evidence, stage1, stage2, stage3, stage4, "proposal_evidence_not_from_stage2"))
    changed_diagnosis = {**proposal, "diagnosis": "Unsupported operator selected the wrong file."}
    cases.append((changed_diagnosis, stage1, stage2, stage3, stage4, "diagnosis_changed"))
    changed_path = {**proposal, "implementation_path": "DELTA.py"}
    cases.append((changed_path, stage1, stage2, stage3, stage4, "implementation_path_changed"))
    evaluator_mutation = {**proposal}
    bad_strategy = {**stage4, "files_allowed": [IMPL, TEST]}
    cases.append((evaluator_mutation, stage1, stage2, stage3, bad_strategy, "strategy_mutates_evaluator"))
    wildcard_strategy = {**stage4, "files_allowed": [IMPL, "orchestration/runtime/*"]}
    cases.append((proposal, stage1, stage2, stage3, wildcard_strategy, "prohibited_or_broad_strategy_path"))
    success_claim = {**proposal, "expected_behavioral_change": "Tests now pass and the defect is fixed."}
    cases.append((success_claim, stage1, stage2, stage3, stage4, "success_claim_prohibited"))
    authority = {**proposal, "required_authority": ("network",)}
    cases.append((authority, stage1, stage2, stage3, stage4, "required_authority_changed"))

    for candidate, s1, s2, s3, s4, reason in cases:
        audit = audit_cognitive_proposal_consistency(
            evidence_selection=s1,
            diagnosis=s2,
            path_selection=s3,
            strategy=s4,
            proposal=candidate,
        )
        assert audit["accepted"] is False
        assert reason in audit["reasons"]


def test_assembled_proposal_missing_semantic_field_rejected_without_invention():
    stage1, stage2, stage3, stage4, proposal = _assembled_inputs()
    bad = {**proposal}
    bad.pop("uncertainty")

    result = validate_assembled_cognitive_proposal(
        proposal=bad,
        evidence_selection=stage1,
        evidence_packet=packet(),
        diagnosis=stage2,
        path_selection=stage3,
        strategy=stage4,
        allowlist=allowlist(),
        allowed_authority=AUTHORITY,
    )

    assert result["accepted"] is False
    assert "missing_required_cognitive_fields" in result["grounding_result"]["reasons"]


def test_monolithic_versus_staged_comparison_record_shape():
    record = {
        "monolithic": {"json_valid": True, "required_field_completion": False},
        "staged": {"json_valid": True, "required_field_completion": True},
        "model_call_count": 4,
    }

    assert set(record) == {"monolithic", "staged", "model_call_count"}


def test_stage1_internal_request_is_not_serialized_directly_to_model_messages():
    internal = build_stage1_internal_request(
        request_id="r1",
        model_id="m1",
        problem_id="p1",
        evidence_packet=packet(),
        budget={"maximum": 6},
    )
    messages = stage1_model_messages(internal)
    user = messages[1]["content"]

    assert internal["request_id"] == "r1"
    assert "request_id" not in user
    assert "budget" not in user
    assert "AVAILABLE EVIDENCE" in user


def test_stage1_model_facing_input_and_output_roots_are_distinct():
    internal = build_stage1_internal_request(
        request_id="r1",
        model_id="m1",
        problem_id="p1",
        evidence_packet=packet(),
        budget={"maximum": 6},
    )
    user = stage1_model_messages(internal)[1]["content"]

    assert '"evidence_selection":' not in user
    assert "result_type" in user
    assert "AVAILABLE EVIDENCE" in user


def test_stage1_model_facing_request_preserves_problem_statement_claim_when_categories_absent():
    evidence_packet = {
        **packet(),
        "problem_statement": "Duplicate replay must not treat stale rejected advisory artifacts as passed.",
    }
    internal = build_stage1_internal_request(
        request_id="r1",
        model_id="m1",
        problem_id="p1",
        evidence_packet=evidence_packet,
        budget={"maximum": 6},
    )
    user = stage1_model_messages(internal)[1]["content"]

    assert "Duplicate replay must not treat stale rejected advisory artifacts as passed." in user
    assert "Required claims:\n[]" not in user


def test_stage1_revision_is_stateless_and_leaks_no_correct_evidence_choice():
    internal = build_stage1_internal_request(
        request_id="r1",
        model_id="m1",
        problem_id="p1",
        evidence_packet=packet(),
        budget={"maximum": 6},
    )
    messages = stage1_revision_messages(
        internal_request=internal,
        validation={"reasons": ("wrong_result_type",)},
        response_keys=("evidence_packet",),
    )
    text = messages[1]["content"]

    assert "wrong_result_type" in text
    assert "Do not echo AVAILABLE EVIDENCE" in text
    assert "ck-adapter-fixture:duplicate-replay" not in text


def test_stage1_fixture_integrity_accepts_visible_stage1_fixture():
    result = audit_stage1_fixture_integrity(packet())

    assert result["accepted"] is True
    assert result["source_count"] == 1


def test_stage1_fixture_integrity_rejects_missing_visible_text():
    bad = {"sources": [{"source_id": "s", "excerpt_id": "e", "path": "p"}]}

    result = audit_stage1_fixture_integrity(bad)

    assert result["accepted"] is False
    assert "missing_visible_text" in result["reasons"]
