from __future__ import annotations

import json

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _objective():
    return gsr.make_development_objective("Observe runtime evidence without diagnosing.", sequence=10)


def _evidence(objective, *, fingerprint: str = "same-fingerprint", sequence: int = 10, telemetry_only: bool = False):
    return gsr.make_observation_evidence(
        objective.objective_id,
        source_subsystem="conversation_router",
        source_type="operator_supplied_transcript",
        source_reference="reports/operator_pilot/conversation_log.md",
        observed_input="what were we discussing before that",
        observed_output="pending local-model consent repeated",
        expected_transition="discourse_history_recall",
        observed_transition="pending_local_model_consent",
        first_incorrect_transition="pending_consent_preempts_discourse_recall",
        sequence=sequence,
        user_visible=not telemetry_only,
        telemetry_only=telemetry_only,
        live_runtime=True,
        evidence_fingerprint=fingerprint,
    )


def _observation(objective, evidence):
    return gsr.make_observation(
        objective.objective_id,
        source_subsystem=evidence.source_subsystem,
        observed_behavior=evidence.observed_transition,
        expected_behavior=evidence.expected_transition,
        evidence_references=(evidence.evidence_id,),
        confidence=0.7,
        uncertainty="operator_transcript",
        reproducibility="single_sequence",
        user_visible=evidence.user_visible,
        telemetry_only=evidence.telemetry_only,
    )


def _observation_with_confidence_and_severity(objective, evidence, *, confidence: float, severity: str):
    return gsr.make_observation(
        objective.objective_id,
        source_subsystem=evidence.source_subsystem,
        observed_behavior=evidence.observed_transition,
        expected_behavior=evidence.expected_transition,
        evidence_references=(evidence.evidence_id,),
        confidence=confidence,
        uncertainty="operator_transcript",
        severity=severity,
        reproducibility="single_sequence",
        user_visible=evidence.user_visible,
        telemetry_only=evidence.telemetry_only,
    )


def _recorded_ledger():
    objective = _objective()
    evidence = _evidence(objective)
    observation = _observation(objective, evidence)
    ledger = gsr.make_observation_ledger(objective.objective_id, sequence=10)
    result = gsr.record_observation(ledger, observation, evidence)
    assert result.entry is not None
    return objective, evidence, observation, result.state, result.entry


def _ledger_with_two_entries():
    objective, evidence, observation, ledger, first = _recorded_ledger()
    replacement_evidence = _evidence(objective, fingerprint="replacement-fingerprint", sequence=11)
    replacement_observation = _observation(objective, replacement_evidence)
    result = gsr.record_observation(ledger, replacement_observation, replacement_evidence)
    assert result.entry is not None
    return objective, evidence, observation, result.state, first, result.entry


def test_observation_evidence_validation_fails_closed_for_incomplete_or_side_effect_evidence():
    objective = _objective()
    incomplete = _evidence(objective, fingerprint="incomplete")
    incomplete = gsr.ObservationEvidence(**{**gsr.serialize(incomplete), "evidence_complete": False})
    provider = gsr.make_observation_evidence(
        objective.objective_id,
        source_subsystem="provider",
        source_type="external_provider",
        source_reference="provider://call",
        observed_input="prompt",
        observed_output="response",
        expected_transition="no_provider_call",
        observed_transition="provider_call",
        first_incorrect_transition="provider_call_started",
        provider_involved=True,
    )

    assert gsr.validate_observation_evidence(incomplete) == (False, "evidence_incomplete")
    assert gsr.validate_observation_evidence(provider) == (False, "prohibited_side_effect_in_evidence")


def test_valid_observation_enters_pending_review_not_retained():
    _, evidence, _, ledger, entry = _recorded_ledger()

    assert evidence.evidence_id in ledger.evidence_index
    assert entry.lifecycle_state == "pending_review"
    assert entry.review_status == "operator_review_required"
    assert entry.ledger_entry_id in ledger.review_queue
    assert entry.ledger_entry_id not in ledger.diagnosis_review_queue


def test_observation_cannot_review_itself_and_no_diagnosis_or_proposal_is_created():
    _, _, observation, _, entry = _recorded_ledger()

    assert gsr.observation_can_review_itself(observation) is False
    assert gsr.ledger_entry_creates_diagnosis(entry) is False
    assert gsr.ledger_entry_creates_repair_proposal(entry) is False
    assert gsr.observation_auto_diagnoses(observation) is False


def test_duplicate_linking_is_conservative_and_does_not_delete_evidence():
    objective, _, _, ledger, first = _recorded_ledger()
    duplicate_evidence = _evidence(objective, fingerprint="same-fingerprint", sequence=11)
    duplicate_observation = _observation(objective, duplicate_evidence)

    result = gsr.record_observation(ledger, duplicate_observation, duplicate_evidence)

    assert result.accepted is True
    assert result.entry is not None
    assert result.entry.duplicate_of == first.ledger_entry_id
    assert result.state.duplicate_links[result.entry.ledger_entry_id] == first.ledger_entry_id
    assert len(result.state.entries) == 2
    assert duplicate_evidence.evidence_id in result.state.evidence_index


def test_similar_observation_without_matching_fingerprint_is_not_silently_deduped():
    objective, _, _, ledger, _ = _recorded_ledger()
    similar_evidence = _evidence(objective, fingerprint="different-fingerprint", sequence=11)
    similar_observation = _observation(objective, similar_evidence)

    result = gsr.record_observation(ledger, similar_observation, similar_evidence)

    assert result.accepted is True
    assert result.entry is not None
    assert result.entry.duplicate_of is None
    assert len(result.state.entries) == 2


def test_corroboration_requires_operator_review_and_does_not_create_diagnosis():
    _, _, _, ledger, entry = _recorded_ledger()
    self_decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="corroborated",
        rationale="DELTA cannot self-review observations.",
        sequence=11,
        operator_authority="DELTA_SELF_AUTHORITY",
    )
    rejected = gsr.review_observation_entry(ledger, self_decision)
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="corroborated",
        rationale="operator marks repeated transcript as corroborating evidence",
        sequence=11,
    )
    accepted = gsr.review_observation_entry(ledger, decision)

    assert rejected.accepted is False
    assert rejected.reason == "operator_authority_required"
    assert accepted.accepted is True
    assert accepted.entry is not None
    assert accepted.entry.lifecycle_state == "corroborated"
    assert accepted.entry.corroboration_count == 1
    assert accepted.creates_diagnosis_candidate is False
    assert accepted.entry.ledger_entry_id not in accepted.state.diagnosis_review_queue


def test_severity_and_confidence_do_not_bypass_pending_review():
    objective = _objective()
    evidence = _evidence(objective, fingerprint="severe-confident")
    observation = _observation_with_confidence_and_severity(objective, evidence, confidence=0.99, severity="critical")
    ledger = gsr.make_observation_ledger(objective.objective_id, sequence=10)

    result = gsr.record_observation(ledger, observation, evidence)

    assert result.accepted is True
    assert result.entry is not None
    assert result.entry.lifecycle_state == "pending_review"
    assert result.entry.diagnosis_eligibility_status == "not_eligible"
    assert result.creates_diagnosis_candidate is False
    assert result.entry.ledger_entry_id in result.state.review_queue
    assert result.entry.ledger_entry_id not in result.state.diagnosis_review_queue


def test_valid_operator_decision_applies_retained_disposition_and_records_decision_id():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="operator retains the observation in the inert ledger",
        sequence=11,
    )

    result = gsr.review_observation_entry(ledger, decision)

    assert result.accepted is True
    assert result.entry is not None
    assert result.entry.lifecycle_state == "retained"
    assert result.entry.operator_disposition == "retained"
    assert decision.decision_id in result.state.review_decision_ids
    assert result.creates_diagnosis_candidate is False


def test_one_shot_review_decision_cannot_be_reused_after_success():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="operator retains the observation once",
        sequence=11,
    )

    first = gsr.review_observation_entry(ledger, decision)
    second = gsr.review_observation_entry(first.state, decision)

    assert first.accepted is True
    assert second.accepted is False
    assert second.reason == "decision_already_used"


def test_failed_review_decisions_do_not_consume_decision_id():
    _, _, _, ledger, entry = _recorded_ledger()
    non_operator = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="DELTA-generated decision must not count",
        sequence=11,
        operator_authority="DELTA_SELF_AUTHORITY",
    )
    consumed = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="pre-consumed decision must fail closed",
        sequence=11,
    )
    consumed = gsr.ObservationReviewDecision(**{**gsr.serialize(consumed), "consumed": True})

    non_operator_result = gsr.review_observation_entry(ledger, non_operator)
    consumed_result = gsr.review_observation_entry(ledger, consumed)

    assert non_operator_result.accepted is False
    assert non_operator_result.reason == "operator_authority_required"
    assert non_operator.decision_id not in non_operator_result.state.review_decision_ids
    assert consumed_result.accepted is False
    assert consumed_result.reason == "decision_consumed"
    assert consumed.decision_id not in consumed_result.state.review_decision_ids


def test_wrong_target_review_decision_fails_without_consuming_identity():
    _, _, _, ledger, entry = _recorded_ledger()
    wrong_target = gsr.make_observation_review_decision(
        "missing-entry",
        decision="approve",
        allowed_transition="retained",
        rationale="decision targets the wrong entry",
        sequence=11,
    )

    result = gsr.review_observation_entry(ledger, wrong_target)

    assert result.accepted is False
    assert result.reason == "entry_not_found"
    assert wrong_target.decision_id not in result.state.review_decision_ids
    assert entry.lifecycle_state == "pending_review"


def test_serialization_preserves_used_decision_ids_and_does_not_reactivate_decision():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="operator retains before serialization",
        sequence=11,
    )
    first = gsr.review_observation_entry(ledger, decision)
    restored = gsr.deserialize(gsr.ObservationLedgerState, json.loads(json.dumps(gsr.serialize(first.state))))

    second = gsr.review_observation_entry(restored, decision)

    assert decision.decision_id in restored.review_decision_ids
    assert second.accepted is False
    assert second.reason == "decision_already_used"


def test_supported_operator_dispositions_apply_as_inert_ledger_state():
    supported = (
        "retained",
        "rejected",
        "duplicate",
        "corroborated",
        "expired",
        "insufficient_evidence",
        "non_defect",
        "telemetry_only",
        "suspended",
    )
    for index, disposition in enumerate(supported, start=20):
        _, _, _, ledger, entry = _recorded_ledger()
        duplicate_of = entry.ledger_entry_id if disposition == "duplicate" else None
        decision = gsr.make_observation_review_decision(
            entry.ledger_entry_id,
            decision="approve",
            allowed_transition=disposition,
            rationale=f"operator marks {disposition}",
            sequence=index,
            duplicate_of=duplicate_of,
        )

        result = gsr.review_observation_entry(ledger, decision)

        assert result.accepted is True
        assert result.entry is not None
        assert result.entry.lifecycle_state == disposition
        assert result.entry.operator_disposition == disposition
        assert result.creates_diagnosis_candidate is False
        assert gsr.ledger_entry_creates_repair_proposal(result.entry) is False


def test_terminal_disposition_states_cannot_advance_after_operator_review():
    for terminal_state in ("rejected", "expired", "suspended", "superseded"):
        if terminal_state == "superseded":
            _, _, _, ledger, entry, replacement = _ledger_with_two_entries()
            replacement_id = replacement.ledger_entry_id
        else:
            _, _, _, ledger, entry = _recorded_ledger()
            replacement_id = None
        first = gsr.make_observation_review_decision(
            entry.ledger_entry_id,
            decision="approve",
            allowed_transition=terminal_state,
            rationale=f"operator marks {terminal_state}",
            sequence=20,
            supersedes=replacement_id,
        )
        reviewed = gsr.review_observation_entry(ledger, first)
        second = gsr.make_observation_review_decision(
            entry.ledger_entry_id,
            decision="approve",
            allowed_transition="retained",
            rationale="attempt to advance terminal state",
            sequence=21,
        )

        advanced = gsr.review_observation_entry(reviewed.state, second)

        assert reviewed.accepted is True
        assert advanced.accepted is False
        assert advanced.reason == "entry_state_cannot_advance"
        assert reviewed.entry is not None
        assert gsr.ledger_entry_can_advance(reviewed.entry) is False


def test_non_operator_disposition_still_fails_closed_without_consuming_decision():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="rejected",
        rationale="self-generated rejection is invalid",
        sequence=20,
        operator_authority="DELTA_GENERATED",
    )

    result = gsr.review_observation_entry(ledger, decision)

    assert result.accepted is False
    assert result.reason == "operator_authority_required"
    assert decision.decision_id not in result.state.review_decision_ids


def test_sequence_window_expiration_is_deterministic_and_preserves_evidence():
    _, evidence, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="operator retains for a bounded sequence window",
        sequence=20,
        expires_after_sequence=22,
        retention_policy="retain_for_sequence_window",
    )
    retained = gsr.review_observation_entry(ledger, decision)

    not_yet = gsr.expire_observation_entries(retained.state, current_sequence=22)
    expired = gsr.expire_observation_entries(retained.state, current_sequence=23)
    expired_payload = next(payload for payload in expired.entries if payload["ledger_entry_id"] == entry.ledger_entry_id)

    assert entry.ledger_entry_id not in not_yet.expired_entries
    assert entry.ledger_entry_id in expired.expired_entries
    assert expired_payload["lifecycle_state"] == "expired"
    assert expired_payload["operator_disposition"] == "expired"
    assert evidence.evidence_id in expired.evidence_index
    assert expired_payload in expired.entries


def test_objective_closure_expiration_requires_explicit_closed_input():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="operator retains until objective closes",
        sequence=20,
        retention_policy="retain_until_objective_closed",
    )
    retained = gsr.review_observation_entry(ledger, decision)

    open_objective = gsr.expire_observation_entries(retained.state, current_sequence=100, objective_closed=False)
    closed_objective = gsr.expire_observation_entries(retained.state, current_sequence=100, objective_closed=True)

    assert entry.ledger_entry_id not in open_objective.expired_entries
    assert entry.ledger_entry_id in closed_objective.expired_entries


def test_manual_retention_does_not_expire_automatically():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="operator chooses manual retention",
        sequence=20,
        expires_after_sequence=21,
        retention_policy="manual_retention",
    )
    retained = gsr.review_observation_entry(ledger, decision)

    expired = gsr.expire_observation_entries(retained.state, current_sequence=999, objective_closed=True)

    assert entry.ledger_entry_id not in expired.expired_entries
    payload = next(payload for payload in expired.entries if payload["ledger_entry_id"] == entry.ledger_entry_id)
    assert payload["lifecycle_state"] == "retained"


def test_unknown_retention_policy_fails_closed_without_consuming_decision():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="retained",
        rationale="unknown retention policy must fail",
        sequence=20,
        retention_policy="forever_without_review",
    )

    result = gsr.review_observation_entry(ledger, decision)

    assert result.accepted is False
    assert result.reason == "unknown_retention_policy"
    assert decision.decision_id not in result.state.review_decision_ids


def test_supersession_requires_existing_replacement_and_preserves_both_entries():
    _, _, _, ledger, first, replacement = _ledger_with_two_entries()
    decision = gsr.make_observation_review_decision(
        first.ledger_entry_id,
        decision="approve",
        allowed_transition="superseded",
        rationale="operator supersedes old observation with a later reviewed entry",
        sequence=30,
        supersedes=replacement.ledger_entry_id,
    )

    result = gsr.review_observation_entry(ledger, decision)

    assert result.accepted is True
    assert len(result.state.entries) == 2
    assert result.entry is not None
    assert result.entry.lifecycle_state == "superseded"
    assert result.entry.superseded_by == replacement.ledger_entry_id
    assert result.state.supersession_links[first.ledger_entry_id] == replacement.ledger_entry_id
    replacement_payload = next(payload for payload in result.state.entries if payload["ledger_entry_id"] == replacement.ledger_entry_id)
    assert replacement_payload["lifecycle_state"] == "pending_review"
    assert replacement_payload["diagnosis_eligibility_status"] == "not_eligible"


def test_supersession_fails_when_replacement_is_missing_or_self_targeted():
    _, _, _, ledger, first = _recorded_ledger()
    missing = gsr.make_observation_review_decision(
        first.ledger_entry_id,
        decision="approve",
        allowed_transition="superseded",
        rationale="missing replacement must fail",
        sequence=30,
        supersedes="missing-entry",
    )
    self_target = gsr.make_observation_review_decision(
        first.ledger_entry_id,
        decision="approve",
        allowed_transition="superseded",
        rationale="self replacement must fail",
        sequence=31,
        supersedes=first.ledger_entry_id,
    )

    missing_result = gsr.review_observation_entry(ledger, missing)
    self_result = gsr.review_observation_entry(ledger, self_target)

    assert missing_result.accepted is False
    assert missing_result.reason == "replacement_entry_not_found"
    assert self_target.decision_id not in self_result.state.review_decision_ids
    assert self_result.accepted is False
    assert self_result.reason == "replacement_entry_required"


def test_superseded_entry_cannot_advance_but_replacement_remains_pending():
    _, _, _, ledger, first, replacement = _ledger_with_two_entries()
    supersede = gsr.make_observation_review_decision(
        first.ledger_entry_id,
        decision="approve",
        allowed_transition="superseded",
        rationale="operator supersedes old observation",
        sequence=30,
        supersedes=replacement.ledger_entry_id,
    )
    superseded = gsr.review_observation_entry(ledger, supersede)
    advance = gsr.make_observation_review_decision(
        first.ledger_entry_id,
        decision="approve",
        allowed_transition="diagnosis_review_eligible",
        rationale="terminal superseded entries cannot advance",
        sequence=31,
    )

    advanced = gsr.review_observation_entry(superseded.state, advance)

    assert advanced.accepted is False
    assert advanced.reason == "entry_state_cannot_advance"
    replacement_payload = next(payload for payload in superseded.state.entries if payload["ledger_entry_id"] == replacement.ledger_entry_id)
    assert replacement_payload["lifecycle_state"] == "pending_review"


def test_non_telemetry_entry_can_be_marked_diagnosis_review_eligible_without_creating_objects():
    _, _, _, ledger, entry = _recorded_ledger()
    decision = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="diagnosis_review_eligible",
        rationale="operator allows diagnosis review only",
        sequence=40,
    )

    result = gsr.review_observation_entry(ledger, decision)

    assert result.accepted is True
    assert result.entry is not None
    assert result.entry.lifecycle_state == "diagnosis_review_eligible"
    assert result.entry.diagnosis_eligibility_status == "eligible_for_review"
    assert result.entry.ledger_entry_id in result.state.diagnosis_review_queue
    assert result.creates_diagnosis_candidate is False
    assert gsr.ledger_entry_creates_diagnosis(result.entry) is False
    assert gsr.ledger_entry_creates_repair_proposal(result.entry) is False


def test_telemetry_only_requires_disposition_then_separate_reclassifying_decision():
    objective = _objective()
    evidence = _evidence(objective, fingerprint="telemetry", telemetry_only=True)
    observation = _observation(objective, evidence)
    ledger = gsr.make_observation_ledger(objective.objective_id, sequence=10)
    recorded = gsr.record_observation(ledger, observation, evidence)
    assert recorded.entry is not None
    direct = gsr.make_observation_review_decision(
        recorded.entry.ledger_entry_id,
        decision="approve",
        allowed_transition="diagnosis_review_eligible",
        rationale="direct telemetry eligibility must fail",
        sequence=40,
    )
    direct_with_reclass = gsr.make_observation_review_decision(
        recorded.entry.ledger_entry_id,
        decision="approve",
        allowed_transition="diagnosis_review_eligible",
        rationale="reclassification without telemetry disposition must fail",
        sequence=41,
        reclassifies_telemetry=True,
    )
    telemetry_disposition = gsr.make_observation_review_decision(
        recorded.entry.ledger_entry_id,
        decision="approve",
        allowed_transition="telemetry_only",
        rationale="operator marks evidence as telemetry-only first",
        sequence=42,
    )

    direct_result = gsr.review_observation_entry(recorded.state, direct)
    reclass_without_disposition = gsr.review_observation_entry(recorded.state, direct_with_reclass)
    telemetry_marked = gsr.review_observation_entry(recorded.state, telemetry_disposition)
    eligible_decision = gsr.make_observation_review_decision(
        recorded.entry.ledger_entry_id,
        decision="approve",
        allowed_transition="diagnosis_review_eligible",
        rationale="operator explicitly reclassifies telemetry for diagnosis review",
        sequence=43,
        reclassifies_telemetry=True,
    )
    eligible = gsr.review_observation_entry(telemetry_marked.state, eligible_decision)

    assert direct_result.accepted is False
    assert direct_result.reason == "telemetry_reclassification_required"
    assert reclass_without_disposition.accepted is False
    assert reclass_without_disposition.reason == "telemetry_disposition_required"
    assert telemetry_marked.accepted is True
    assert eligible.accepted is True
    assert eligible.entry is not None
    assert eligible.entry.lifecycle_state == "diagnosis_review_eligible"
    assert eligible.creates_diagnosis_candidate is False


def test_frequency_and_corroboration_do_not_trigger_diagnosis_eligibility():
    _, _, _, ledger, entry = _recorded_ledger()
    high_occurrence = gsr.ObservationLedgerEntry(**{**gsr.serialize(entry), "occurrence_count": 99, "corroboration_count": 12})
    synthetic_state = gsr.ObservationLedgerState(
        ledger_id=ledger.ledger_id,
        objective_id=ledger.objective_id,
        sequence=ledger.sequence,
        entries=(gsr.serialize(high_occurrence),),
        evidence_index=dict(ledger.evidence_index),
        review_queue=(high_occurrence.ledger_entry_id,),
    )

    payload = synthetic_state.entries[0]

    assert payload["diagnosis_eligibility_status"] == "not_eligible"
    assert high_occurrence.ledger_entry_id not in synthetic_state.diagnosis_review_queue
    assert gsr.ledger_entry_creates_diagnosis(high_occurrence) is False


def test_invalid_review_transitions_fail_closed():
    _, _, _, ledger, entry = _recorded_ledger()
    raw = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="raw",
        rationale="raw is not an allowed review outcome",
        sequence=40,
    )
    unknown = gsr.make_observation_review_decision(
        entry.ledger_entry_id,
        decision="approve",
        allowed_transition="mystery_state",
        rationale="unknown state must fail",
        sequence=41,
    )

    raw_result = gsr.review_observation_entry(ledger, raw)
    unknown_result = gsr.review_observation_entry(ledger, unknown)

    assert raw_result.accepted is False
    assert raw_result.reason == "invalid_review_transition"
    assert raw.decision_id not in raw_result.state.review_decision_ids
    assert unknown_result.accepted is False
    assert unknown_result.reason == "unknown_ledger_state"


def test_serialization_preserves_links_denial_states_and_evidence_flags():
    objective, _, _, ledger, first, replacement = _ledger_with_two_entries()
    duplicate_evidence = _evidence(objective, fingerprint="same-fingerprint", sequence=12)
    duplicate_observation = _observation(objective, duplicate_evidence)
    duplicated = gsr.record_observation(ledger, duplicate_observation, duplicate_evidence)
    assert duplicated.entry is not None
    corroborate = gsr.make_observation_review_decision(
        duplicated.entry.ledger_entry_id,
        decision="approve",
        allowed_transition="corroborated",
        rationale="operator marks duplicate as corroborating",
        sequence=40,
    )
    corroborated = gsr.review_observation_entry(duplicated.state, corroborate)
    supersede = gsr.make_observation_review_decision(
        first.ledger_entry_id,
        decision="approve",
        allowed_transition="superseded",
        rationale="operator supersedes first entry",
        sequence=41,
        supersedes=replacement.ledger_entry_id,
    )
    superseded = gsr.review_observation_entry(corroborated.state, supersede)
    restored = gsr.deserialize(gsr.ObservationLedgerState, json.loads(json.dumps(gsr.serialize(superseded.state))))

    assert restored.duplicate_links == superseded.state.duplicate_links
    assert restored.supersession_links == superseded.state.supersession_links
    assert restored.review_decision_ids == superseded.state.review_decision_ids
    assert duplicate_evidence.evidence_id in restored.evidence_index
    evidence_payload = restored.evidence_index[duplicate_evidence.evidence_id]
    assert evidence_payload["synthetic_fixture"] is False
    assert evidence_payload["live_runtime"] is True
    assert evidence_payload["provider_involved"] is False
    assert evidence_payload["model_involved"] is False
    superseded_payload = next(payload for payload in restored.entries if payload["ledger_entry_id"] == first.ledger_entry_id)
    assert superseded_payload["lifecycle_state"] == "superseded"
    assert superseded_payload["superseded_by"] == replacement.ledger_entry_id
