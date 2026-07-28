import json
from dataclasses import FrozenInstanceError

import pytest

from orchestration.runtime.cognitive_claim_relations import (
    LIFECYCLE_STATES,
    RELATION_TYPES,
    REQUIRED_REPORT_FILES,
    STATUS_PASSED,
    ClaimRelationStateBundle,
    GovernedClaimRecord,
    GovernedWorkItem,
    apply_bounded_exception,
    apply_explicit_correction,
    apply_scoped_preference_update,
    apply_temporal_transition,
    claim_schema,
    classify_relation,
    construct_claim,
    construct_relation,
    expose_for_evaluator,
    first_missing_transition,
    invalidate_relation,
    link_confirmation,
    link_duplicate,
    mark_unrelated,
    negative_controls,
    operator_resolution_key,
    proposal_amendment_record,
    read_bundle,
    reconstruct_bundle,
    register_claim,
    register_contradiction,
    register_uncertain_conflict,
    relation_identity,
    relation_schema,
    request_operator_resolution,
    resolve_by_grounded_evidence,
    resolve_by_operator,
    revoke_authority,
    run_claim_relation_contract_report,
    serialize_bundle,
    validate_bundle,
    validate_relation,
    write_bundle,
)
from orchestration.runtime.cognitive_contradiction_evaluation import evaluate_observation, behavioral_cases


def _claim(value="PostgreSQL", **overrides):
    payload = {
        "subject_scope": "project_database",
        "claim_text": f"The project database is {value}.",
        "normalized_content": {"subject": "project_database", "predicate": "database", "value": value},
        "provenance_refs": (f"turn:{value}",),
        "authority_source": "operator",
    }
    payload.update(overrides)
    return construct_claim(**payload)


def _bundle(*claims, work_items=()):
    return ClaimRelationStateBundle(claims=tuple(claims), work_items=tuple(work_items))


def _case(case_id):
    return {case.case_id: case for case in behavioral_cases()}[case_id]


def test_governed_claim_construction_is_immutable_and_complete():
    claim = _claim()
    assert isinstance(claim, GovernedClaimRecord)
    assert claim.claim_id.startswith("claim-")
    assert claim.claim_digest
    assert claim.lifecycle_state == "current"
    assert claim.schema_version
    assert not validate_bundle(_bundle(claim))
    with pytest.raises(FrozenInstanceError):
        claim.lifecycle_state = "superseded"


def test_deterministic_claim_identity_and_digest():
    first = _claim()
    second = _claim()
    assert first.claim_id == second.claim_id
    assert first.claim_digest == second.claim_digest


def test_scope_sensitive_identity_rejects_raw_text_only_identity():
    global_claim = construct_claim(claim_text="Use concise reports.", normalized_content={"preference": "concise_reports"}, applicability_scope="global", provenance_refs=("turn:1",))
    project_claim = construct_claim(claim_text="Use concise reports.", normalized_content={"preference": "concise_reports"}, applicability_scope="audit_packet", provenance_refs=("turn:2",))
    assert global_claim.claim_text == project_claim.claim_text
    assert global_claim.claim_id != project_claim.claim_id
    assert negative_controls()["claim_identity_only_raw_text"].startswith("rejected")


def test_relation_identity_and_schema_are_typed_and_distinct():
    left = _claim("PostgreSQL")
    right = _claim("SQLite")
    confirmation = construct_relation(left, right, relation_type="confirms")
    contradiction = construct_relation(left, right, relation_type="direct_contradiction", resolution_state="unresolved", authority_effect="no_winner_without_authority_or_evidence")
    assert confirmation.relation_id != contradiction.relation_id
    assert relation_identity(left_claim_id=left.claim_id, right_claim_id=right.claim_id, relation_type="confirms", relation_scope="same_subject_scope", temporal_order="left_before_right", authority_effect="none") == confirmation.relation_id
    assert claim_schema()["immutable"] is True
    assert relation_schema()["immutable"] is True


def test_confirmation_and_duplicate_restatement_are_not_contradictions():
    left = _claim("PostgreSQL")
    right = _claim("PostgreSQL")
    bundle = _bundle(left, right)
    confirmed = link_confirmation(bundle, left, right).after_state
    duplicated = link_duplicate(confirmed, left, right).after_state
    assert {item.relation_type for item in duplicated.relations} == {"confirms", "duplicate_restatement"}
    assert classify_relation(left, right) == "duplicate_restatement"


def test_explicit_correction_supersedes_without_deleting_prior_claim():
    left = construct_claim(subject_scope="appointment", claim_text="The appointment is Tuesday.", normalized_content={"subject": "appointment", "day": "Tuesday"}, provenance_refs=("turn:1",))
    right = construct_claim(subject_scope="appointment", claim_text="Correction: the appointment is Wednesday.", normalized_content={"subject": "appointment", "day": "Wednesday"}, provenance_refs=("turn:2",))
    result = apply_explicit_correction(_bundle(left, right), left, right)
    by_id = {claim.claim_id: claim for claim in result.after_state.claims}
    assert by_id[left.claim_id].lifecycle_state == "superseded"
    assert by_id[right.claim_id].lifecycle_state == "current"
    assert len(result.after_state.claims) == 2
    assert result.relation.relation_type == "explicit_correction"
    assert result.relation.supersedes_claim_id == left.claim_id


def test_direct_contradiction_does_not_make_newest_claim_true():
    left = _claim("PostgreSQL")
    right = _claim("SQLite")
    result = register_contradiction(_bundle(left, right), left, right)
    by_id = {claim.claim_id: claim for claim in result.after_state.claims}
    assert by_id[left.claim_id].lifecycle_state == "current"
    assert by_id[right.claim_id].lifecycle_state == "current"
    assert result.relation.resolution_state == "unresolved"
    assert result.relation.authority_effect == "no_winner_without_authority_or_evidence"


def test_uncertain_conflict_preserves_uncertainty():
    left = _claim("enabled", subject_scope="component")
    right = _claim("disabled", subject_scope="component", claim_text="A log suggests the component may be disabled.", normalized_content={"subject": "component", "state": "maybe_disabled"})
    result = register_uncertain_conflict(_bundle(left, right), left, right)
    assert result.relation.relation_type == "uncertain_conflict"
    assert result.relation.confidence_state == "uncertain"


def test_temporal_transition_is_historical_not_direct_contradiction():
    old = _claim("old", subject_scope="evaluator", temporal_scope="prior")
    new = _claim("new", subject_scope="evaluator", temporal_scope="current")
    result = apply_temporal_transition(_bundle(old, new), old, new)
    by_id = {claim.claim_id: claim for claim in result.after_state.claims}
    assert result.relation.relation_type == "temporal_transition"
    assert by_id[old.claim_id].lifecycle_state == "historical"
    assert classify_relation(old, new) == "temporal_transition"


def test_scoped_preference_update_preserves_broader_preference():
    broad = construct_claim(claim_kind="preference", claim_text="I prefer concise reports.", normalized_content={"preference": "concise"}, applicability_scope="global", provenance_refs=("turn:1",))
    narrow = construct_claim(claim_kind="preference", claim_text="For audit packets, I prefer detailed reports.", normalized_content={"preference": "detailed"}, applicability_scope="audit_packets", provenance_refs=("turn:2",))
    result = apply_scoped_preference_update(_bundle(broad, narrow), broad, narrow)
    by_id = {claim.claim_id: claim for claim in result.after_state.claims}
    assert by_id[broad.claim_id].lifecycle_state == "current"
    assert by_id[narrow.claim_id].lifecycle_state == "conditionally_current"
    assert result.relation.relation_scope == "audit_packets"


def test_bounded_exception_preserves_original_rule_and_expiration():
    rule = construct_claim(claim_kind="policy", claim_text="No external providers are allowed.", normalized_content={"policy": "no_external_providers"}, applicability_scope="global", provenance_refs=("turn:1",))
    exception = construct_claim(claim_kind="policy_exception", claim_text="Use the approved local provider only for this gate.", normalized_content={"exception": "local_provider_gate_only"}, applicability_scope="gate_1b", provenance_refs=("turn:2",))
    result = apply_bounded_exception(_bundle(rule, exception), rule, exception, expiration="completion")
    by_id = {claim.claim_id: claim for claim in result.after_state.claims}
    assert by_id[rule.claim_id].lifecycle_state == "current"
    assert by_id[exception.claim_id].lifecycle_state == "conditionally_current"
    assert "expires=completion" in result.relation.relation_scope


def test_authority_revocation_is_prospective_and_durable():
    auth = construct_claim(claim_kind="authorization", claim_text="Sandbox test authorization is approved.", normalized_content={"authorization": "sandbox"}, provenance_refs=("turn:1",))
    revocation = construct_claim(claim_kind="revocation", claim_text="Revoke sandbox test authorization.", normalized_content={"revocation": "sandbox"}, provenance_refs=("turn:2",))
    result = revoke_authority(_bundle(auth, revocation), auth, revocation, affected_work_ids=("pending-sandbox",))
    by_id = {claim.claim_id: claim for claim in result.after_state.claims}
    assert by_id[auth.claim_id].lifecycle_state == "revoked"
    assert result.relation.relation_type == "authority_revocation"
    assert result.after_state.work_items[0].state == "blocked_operator_decision"


def test_unrelated_claims_do_not_block_unrelated_work():
    left = _claim("PostgreSQL", subject_scope="database")
    right = _claim("oil change", subject_scope="vehicle")
    state = _bundle(left, right, work_items=(GovernedWorkItem("independent", "ready"),))
    result = mark_unrelated(state, left, right)
    assert result.relation.relation_type == "unrelated"
    assert result.after_state.work_items[0].state == "ready"
    assert classify_relation(left, right) == "unrelated"


def test_ambiguous_scope_creates_one_operator_request_and_suspends_only_dependent_work():
    left = _claim("uses policy", subject_scope="module_policy")
    right = _claim("does not use policy", subject_scope="module_policy")
    relation = construct_relation(left, right, relation_type="ambiguous_scope", confidence_state="ambiguous", resolution_state="unresolved", authority_effect="operator_boundary_required")
    state = _bundle(left, right, work_items=(GovernedWorkItem("dependent", "ready", (left.claim_id, right.claim_id)), GovernedWorkItem("independent", "ready", ())))
    with_relation = ClaimRelationStateBundle(claims=state.claims, relations=(relation,), work_items=state.work_items)
    result = request_operator_resolution(with_relation, relation, affected_work_ids=("dependent",), recommended_interpretation="ask for module referent")
    duplicate = request_operator_resolution(result.after_state, result.relation, affected_work_ids=("dependent",))
    assert result.operator_request.request_id == duplicate.operator_request.request_id
    assert duplicate.reason == "duplicate_operator_request_suppressed"
    by_work = {item.work_id: item for item in result.after_state.work_items}
    assert by_work["dependent"].state == "blocked_operator_decision"
    assert by_work["independent"].state == "ready"


def test_operator_and_grounded_evidence_resolution_are_deterministic():
    left = _claim("A")
    right = _claim("B")
    contradicted = register_contradiction(_bundle(left, right), left, right).after_state
    requested = request_operator_resolution(contradicted, contradicted.relations[0], affected_work_ids=("dependent",)).after_state
    request = requested.operator_requests[0]
    resolved = resolve_by_operator(requested, request.request_id, decision="use claim B").after_state
    assert resolved.operator_requests[0].consumed is True
    assert resolved.relations[0].resolution_state == "operator_resolved"
    repeat = resolve_by_operator(resolved, request.request_id, decision="use claim B")
    assert repeat.reason == "operator_resolution_already_consumed"
    evidence = resolve_by_grounded_evidence(contradicted, contradicted.relations[0].relation_id, evidence_ref="log:1").after_state
    assert evidence.relations[0].resolution_state == "grounded_evidence_resolved"


def test_restart_persistence_preserves_supersession_revocation_exception_and_requests(tmp_path):
    left = construct_claim(subject_scope="appointment", claim_text="The appointment is Tuesday.", normalized_content={"day": "Tuesday"}, provenance_refs=("turn:1",))
    right = construct_claim(subject_scope="appointment", claim_text="Correction: the appointment is Wednesday.", normalized_content={"day": "Wednesday"}, provenance_refs=("turn:2",))
    corrected = apply_explicit_correction(_bundle(left, right), left, right).after_state
    auth = construct_claim(claim_kind="authorization", claim_text="Approved.", normalized_content={"auth": "yes"}, provenance_refs=("turn:3",))
    revoke = construct_claim(claim_kind="revocation", claim_text="Revoked.", normalized_content={"auth": "revoked"}, provenance_refs=("turn:4",))
    revoked = revoke_authority(ClaimRelationStateBundle(claims=corrected.claims + (auth, revoke), relations=corrected.relations), auth, revoke).after_state
    rule = construct_claim(claim_text="Rule.", normalized_content={"rule": "base"}, provenance_refs=("turn:5",))
    exc = construct_claim(claim_text="Exception.", normalized_content={"exception": "bounded"}, applicability_scope="one_response", provenance_refs=("turn:6",))
    excepted = apply_bounded_exception(ClaimRelationStateBundle(claims=revoked.claims + (rule, exc), relations=revoked.relations), rule, exc).after_state
    pending = request_operator_resolution(excepted, excepted.relations[-1], affected_work_ids=("work",)).after_state
    path = tmp_path / "claim_relations.json"
    write_bundle(path, pending)
    restored = read_bundle(path)
    states = {claim.claim_id: claim.lifecycle_state for claim in restored.claims}
    assert states[left.claim_id] == "superseded"
    assert states[auth.claim_id] == "revoked"
    assert states[exc.claim_id] == "conditionally_current"
    assert restored.operator_requests[0].consumed is False


def test_resolved_request_consumption_survives_restart_without_reactivation(tmp_path):
    left = _claim("A")
    right = _claim("B")
    state = register_contradiction(_bundle(left, right), left, right).after_state
    requested = request_operator_resolution(state, state.relations[0], affected_work_ids=("work",)).after_state
    resolved = resolve_by_operator(requested, requested.operator_requests[0].request_id, decision="resolved").after_state
    write_bundle(tmp_path / "bundle.json", resolved)
    restored = read_bundle(tmp_path / "bundle.json")
    assert restored.operator_requests[0].consumed is True
    duplicate = request_operator_resolution(restored, restored.relations[0], affected_work_ids=("work",))
    assert duplicate.reason == "duplicate_operator_request_suppressed"
    assert duplicate.operator_request.consumed is True


def test_corruption_and_invalid_transition_rejection():
    with pytest.raises(ValueError, match="corrupt_claim_relation_bundle"):
        reconstruct_bundle("{bad")
    left = _claim("A")
    right = _claim("B")
    with pytest.raises(ValueError, match="unsupported_relation_type"):
        construct_relation(left, right, relation_type="generic_conflict")
    relation = construct_relation(left, right, relation_type="ambiguous_scope", confidence_state="ambiguous", resolution_state="unresolved")
    assert "missing_operator_request" in validate_relation(relation)
    with pytest.raises(ValueError, match="relation_not_found"):
        invalidate_relation(_bundle(left, right), "missing")


def test_evaluator_contract_compatibility():
    left = construct_claim(subject_scope="appointment_day", claim_text="The appointment is Tuesday.", normalized_content={"day": "Tuesday"}, provenance_refs=("turn_1",))
    right = construct_claim(subject_scope="appointment_day", claim_text="Correction: the appointment is Wednesday.", normalized_content={"day": "Wednesday"}, provenance_refs=("turn_2",))
    bundle = apply_explicit_correction(_bundle(left, right), left, right).after_state
    observation = expose_for_evaluator(bundle)
    result = evaluate_observation(_case("B"), observation)
    assert result.passed is True
    assert result.classification == "correct_explicit_correction"
    assert "claim_relation_records" in observation
    assert "operator_resolution_request" in observation


def test_proposal_amendment_linkage_and_no_production_integration(tmp_path):
    amendment = proposal_amendment_record("digest")
    assert amendment["baseline_gap_identity"] == "durable_cross_turn_claim_relation_state_missing"
    assert amendment["production_integration_authorized"] is False
    assert amendment["separate_from_replay_validity_proposal"] is True
    result = run_claim_relation_contract_report(tmp_path)
    assert result["status"] == STATUS_PASSED
    for name in REQUIRED_REPORT_FILES:
        assert (tmp_path / name).exists(), name
    activation = json.loads((tmp_path / "activation_block.json").read_text(encoding="utf-8"))
    no_integration = json.loads((tmp_path / "no_production_integration.json").read_text(encoding="utf-8"))
    assert activation["production_integration"] is False
    assert no_integration["memory_path_mutated"] is False


def test_transition_contract_catalog_and_negative_controls():
    transition = first_missing_transition()
    controls = negative_controls()
    assert transition["first_missing_transition"].startswith("claim A is retained")
    assert set(RELATION_TYPES) >= {"explicit_correction", "direct_contradiction", "authority_revocation", "bounded_exception"}
    assert set(LIFECYCLE_STATES) >= {"current", "superseded", "revoked", "conditionally_current", "unresolved", "historical"}
    assert controls["newest_claim_automatically_wins"].startswith("rejected")
    assert controls["duplicate_operator_request"] == "suppressed"
    left = _claim("A")
    right = _claim("B")
    relation = construct_relation(left, right, relation_type="direct_contradiction", resolution_state="unresolved", authority_effect="none")
    assert operator_resolution_key(relation, ("work",)) == operator_resolution_key(relation, ("work",))


def test_register_claim_idempotency_and_invalid_key():
    claim = _claim()
    result = register_claim(ClaimRelationStateBundle(), claim)
    duplicate = register_claim(result.after_state, claim)
    assert duplicate.reason == "duplicate_claim_suppressed"
    with pytest.raises(ValueError, match="invalid_idempotency_key"):
        register_claim(ClaimRelationStateBundle(), claim, idempotency_key="bad")


def test_serialization_roundtrip_preserves_relation_types_and_claim_state():
    left = _claim("PostgreSQL")
    right = _claim("SQLite")
    state = register_contradiction(_bundle(left, right), left, right).after_state
    restored = reconstruct_bundle(serialize_bundle(state))
    assert restored == state
    assert restored.relations[0].relation_type == "direct_contradiction"
    assert restored.claims[0].lifecycle_state == "current"
