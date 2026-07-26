import json
from dataclasses import FrozenInstanceError

import pytest

from orchestration.runtime.cognitive_replay_validity import (
    AUTHORITY_SCOPE,
    REQUIRED_REPORT_FILES,
    STATUS_PASSED,
    GovernedReplayValidityRecord,
    ReplayValidityContext,
    construct_record,
    contract_schema,
    consumer_contract,
    deterministic_duplicate_key,
    evaluate_replay_validity,
    first_missing_transition,
    invalidate_on_source_change,
    mark_consumed,
    negative_controls,
    producer_contract,
    proposal_amendment_record,
    read_record,
    reconstruct_record,
    run_replay_validity_contract_report,
    serialize_record,
    transition_contracts,
    validate_record_contract,
    write_record,
)


def _context(record):
    return ReplayValidityContext(
        evidence_scope_id=record.evidence_scope_id,
        source_digest=record.source_digest,
        accepted_boundary_id=record.accepted_boundary_id,
        consumer_id=record.consumer_id,
        validation_epoch=record.validated_at,
    )


def test_record_construction_is_immutable_and_contains_required_facts():
    record = construct_record()
    assert isinstance(record, GovernedReplayValidityRecord)
    assert record.created_at
    assert record.validated_at
    assert record.rejection_disposition == "none"
    assert record.accepted_boundary_consumed is False
    with pytest.raises(FrozenInstanceError):
        record.accepted_boundary_consumed = True


def test_deterministic_identity_and_digest():
    first = construct_record()
    second = construct_record()
    assert first.record_id == second.record_id
    assert first.digest == second.digest


def test_validation_state_distinctions_are_not_collapsed():
    unknown = construct_record(validation_disposition="unknown")
    stale = construct_record(validation_disposition="invalidated_stale")
    assert evaluate_replay_validity(unknown, _context(unknown)).disposition == "blocked_invalid_validation_state"
    assert evaluate_replay_validity(stale, _context(stale)).disposition == "blocked_invalid_validation_state"


def test_explicit_rejection_semantics():
    record = construct_record(rejection_record_id="reject-1", rejection_disposition="explicitly_rejected")
    result = evaluate_replay_validity(record, _context(record))
    assert result.disposition == "blocked_rejected"
    assert result.reason_code == "explicit_prior_rejection"


def test_current_eligibility():
    record = construct_record()
    result = evaluate_replay_validity(record, _context(record))
    assert result.disposition == "eligible_current"
    assert result.record_digest == record.digest


def test_source_digest_invalidation():
    record = construct_record()
    context = ReplayValidityContext(
        evidence_scope_id=record.evidence_scope_id,
        source_digest="changed-source",
        accepted_boundary_id=record.accepted_boundary_id,
        consumer_id=record.consumer_id,
        validation_epoch=record.validated_at,
    )
    assert evaluate_replay_validity(record, context).disposition == "blocked_stale"
    invalidated = invalidate_on_source_change(record, source_digest="changed-source")
    assert invalidated.validation_disposition == "invalidated_stale"


def test_missing_provenance_blocks():
    record = construct_record(provenance_refs=())
    assert "missing_provenance" in validate_record_contract(record)
    assert evaluate_replay_validity(record, _context(record)).disposition == "blocked_missing_provenance"


def test_duplicate_key_is_deterministic_and_not_payload_similarity():
    record = construct_record()
    context = _context(record)
    key = deterministic_duplicate_key(record, context)
    assert key == deterministic_duplicate_key(record, context)
    assert negative_controls()["duplicate_replay"] == "blocked_duplicate_replay"


def test_duplicate_replay_blocks():
    record = construct_record()
    context = _context(record)
    duplicate_context = ReplayValidityContext(
        evidence_scope_id=context.evidence_scope_id,
        source_digest=context.source_digest,
        accepted_boundary_id=context.accepted_boundary_id,
        consumer_id=context.consumer_id,
        validation_epoch=context.validation_epoch,
        seen_duplicate_keys=(deterministic_duplicate_key(record, context),),
    )
    assert evaluate_replay_validity(record, duplicate_context).disposition == "blocked_duplicate_replay"


def test_one_time_consumption_and_idempotent_same_transition():
    record = construct_record()
    consumed = mark_consumed(record, consumer_id=record.consumer_id, boundary_id=record.accepted_boundary_id)
    assert consumed.accepted_boundary_consumed is True
    assert evaluate_replay_validity(consumed, _context(consumed)).disposition == "blocked_already_consumed"
    assert mark_consumed(consumed, consumer_id=record.consumer_id, boundary_id=record.accepted_boundary_id) == consumed


def test_restart_preserved_consumption(tmp_path):
    record = construct_record()
    consumed = mark_consumed(record, consumer_id=record.consumer_id, boundary_id=record.accepted_boundary_id)
    path = tmp_path / "record.json"
    write_record(path, consumed)
    restored = read_record(path)
    assert restored.accepted_boundary_consumed is True
    assert restored.consumed_at == consumed.consumed_at


def test_invalid_transition_rejection():
    record = construct_record()
    with pytest.raises(ValueError, match="consumer_boundary_mismatch"):
        mark_consumed(record, consumer_id="other-consumer", boundary_id=record.accepted_boundary_id)
    with pytest.raises(ValueError, match="invalid_idempotency_key"):
        mark_consumed(record, consumer_id=record.consumer_id, boundary_id=record.accepted_boundary_id, idempotency_key="bad")


def test_producer_authority_is_bounded_and_cannot_self_certify():
    contract = producer_contract()
    assert contract["producer_must_not_self_certify_behavioral_success"] is True
    assert "implicit_rejection" in contract["prohibited_fields"]


def test_consumer_authority_blocks_noneligible_dispositions():
    contract = consumer_contract()
    assert contract["may_proceed_only_on"] == "eligible_current"
    assert "blocked_rejected" in contract["must_block_or_defer_on"]
    assert "treat_evaluator_success_as_authority" in contract["must_not"]


def test_freshness_policy_required_without_invented_threshold():
    record = construct_record()
    context = ReplayValidityContext(
        evidence_scope_id=record.evidence_scope_id,
        source_digest=record.source_digest,
        accepted_boundary_id=record.accepted_boundary_id,
        consumer_id=record.consumer_id,
        validation_epoch=record.validated_at,
        freshness_policy_id="",
    )
    assert evaluate_replay_validity(record, context).reason_code == "freshness_policy_required"


def test_serialization_reconstruction_and_corruption_handling():
    record = construct_record()
    restored = reconstruct_record(serialize_record(record))
    assert restored == record
    with pytest.raises(ValueError, match="corrupt_replay_validity_record"):
        reconstruct_record("{}")
    corrupt = dict(record.as_record())
    corrupt["schema_version"] = "future"
    with pytest.raises(ValueError, match="unsupported_schema_version"):
        reconstruct_record(json.dumps(corrupt))


def test_rejection_not_inferred_from_missing_success():
    record = construct_record(rejection_record_id="reject-without-disposition", rejection_disposition="none")
    assert "rejection_cannot_be_inferred_without_disposition" in validate_record_contract(record)


def test_consumption_reset_after_restart_rejected():
    record = construct_record(accepted_boundary_consumed=False, consumed_at="2026-01-01T00:00:00Z")
    assert "consumption_reset_after_restart_rejected" in validate_record_contract(record)


def test_contract_schema_and_transition_contracts():
    schema = contract_schema()
    assert schema["immutable"] is True
    assert "accepted_boundary_consumed" in schema["required_missing_facts_represented"]
    transitions = {item["transition"]: item for item in transition_contracts()}
    assert transitions["mark_consumed"]["restart_persistent"] is True
    assert transitions["invalidate_on_source_change"]["after"] == "invalidated_stale"


def test_proposal_amendment_linkage_and_no_activation():
    amendment = proposal_amendment_record()
    assert amendment["proposal_id"] == "cognitive-proposal-a6777613a9e0784f"
    assert amendment["original_proposal_immutable"] is True
    assert amendment["implementation_or_activation_authorized"] is False
    assert amendment["evaluator_remains_unchanged"] is True


def test_no_live_advisory_path_activation(tmp_path):
    result = run_replay_validity_contract_report(tmp_path)
    assert result["status"] == STATUS_PASSED
    assert '"contract_activated": false' in (tmp_path / "activation_block.json").read_text(encoding="utf-8")
    assert '"mutated": false' in (tmp_path / "no_advisory_path_mutation.json").read_text(encoding="utf-8")


def test_report_files_and_immutability_records(tmp_path):
    run_replay_validity_contract_report(tmp_path)
    for name in REQUIRED_REPORT_FILES:
        assert (tmp_path / name).exists(), name
    assert '"proposal_mutated": false' in (tmp_path / "proposal_immutability.json").read_text(encoding="utf-8")
    assert '"evaluator_mutated": false' in (tmp_path / "evaluator_immutability.json").read_text(encoding="utf-8")
    assert first_missing_transition()["required_transition"].startswith("missing behavioral facts")


def test_authority_scope_is_inert_contract_only():
    record = construct_record(authority_scope=AUTHORITY_SCOPE)
    assert validate_record_contract(record) == ()
    broader = construct_record(authority_scope="runtime_activation")
    assert "authority_scope_not_inert_contract" in validate_record_contract(broader)
