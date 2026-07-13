from __future__ import annotations

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _eligible_ledger():
    objective = gsr.make_development_objective("Diagnose only with operator authorization.", sequence=50)
    evidence = gsr.make_observation_evidence(
        objective.objective_id,
        source_subsystem="conversation_router",
        source_type="operator_supplied_transcript",
        source_reference="reports/operator_pilot/conversation_log.md",
        observed_input="what were we discussing before that",
        observed_output="pending local-model consent repeated",
        expected_transition="discourse_history_recall",
        observed_transition="pending_local_model_consent",
        first_incorrect_transition="pending_consent_preempts_discourse_recall",
        sequence=50,
        user_visible=True,
        live_runtime=True,
        evidence_fingerprint="diagnosis-gate-evidence",
    )
    observation = gsr.make_observation(
        objective.objective_id,
        source_subsystem=evidence.source_subsystem,
        observed_behavior=evidence.observed_transition,
        expected_behavior=evidence.expected_transition,
        evidence_references=(evidence.evidence_id,),
        confidence=0.7,
        uncertainty="operator_transcript",
        reproducibility="single_sequence",
        user_visible=True,
    )
    ledger = gsr.make_observation_ledger(objective.objective_id, sequence=50)
    recorded = gsr.record_observation(ledger, observation, evidence)
    assert recorded.entry is not None
    decision = gsr.make_observation_review_decision(
        recorded.entry.ledger_entry_id,
        decision="approve",
        allowed_transition="diagnosis_review_eligible",
        rationale="operator marks entry eligible for diagnosis review",
        sequence=51,
    )
    eligible = gsr.review_observation_entry(recorded.state, decision)
    assert eligible.entry is not None
    return objective, evidence, observation, eligible.state, eligible.entry


def _authorization(entry, *, sequence: int = 52, **kwargs):
    return gsr.make_diagnosis_review_authorization(
        entry.ledger_entry_id,
        allowed_diagnosis_scope=("first_incorrect_transition", "suspected_mechanism"),
        linked_objective_id=entry.objective_id,
        decision_sequence=sequence,
        **kwargs,
    )


def _create(ledger, state, authorization, *, sequence: int = 52):
    return gsr.create_provisional_diagnosis_candidate(
        ledger,
        state,
        authorization,
        suspected_mechanism="pending action handling preempts discourse recall",
        competing_hypotheses=("router concept recall", "pending consent precedence"),
        confidence=0.61,
        uncertainty="single_sequence",
        severity="medium",
        reproducibility="mocked_reproduction",
        scope_estimate="bounded_ui_state_transition",
        affected_components=("DELTA._send_chat",),
        forbidden_components=("router_retrieval", "provider_runtime", "sandbox_execution"),
        sequence=sequence,
    )


def test_eligible_ledger_entry_cannot_create_diagnosis_without_authorization():
    _, _, _, ledger, _ = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()

    assert state.diagnosis_candidates == ()
    assert state.consumed_diagnosis_authorization_ids == ()
    assert ledger.diagnosis_review_queue


def test_valid_operator_authorization_creates_one_provisional_diagnosis_candidate():
    _, evidence, observation, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry)

    result = _create(ledger, state, authorization)

    assert result.accepted is True
    assert result.diagnosis is not None
    assert result.diagnosis.source_ledger_entry_id == entry.ledger_entry_id
    assert result.diagnosis.linked_observations == (observation.observation_id,)
    assert result.evidence_references[0].evidence_id == evidence.evidence_id
    assert result.evidence_references[0].ledger_entry_id == entry.ledger_entry_id
    assert result.diagnosis.provisional is True
    assert result.diagnosis.operator_review_status == "pending_review"
    assert result.creates_repair_proposal is False


def test_wrong_ledger_entry_authorization_fails_without_consuming():
    _, _, _, ledger, _ = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = gsr.make_diagnosis_review_authorization(
        "missing-entry",
        allowed_diagnosis_scope=("first_incorrect_transition",),
        decision_sequence=52,
    )

    result = _create(ledger, state, authorization)

    assert result.accepted is False
    assert result.reason == "ledger_entry_not_found"
    assert authorization.authorization_id not in result.state.consumed_diagnosis_authorization_ids


def test_non_operator_authorization_fails_without_consuming():
    _, _, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry, operator_authority="DELTA_SELF_AUTHORITY")

    result = _create(ledger, state, authorization)

    assert result.accepted is False
    assert result.reason == "operator_authority_required"
    assert authorization.authorization_id not in result.state.consumed_diagnosis_authorization_ids


def test_expired_authorization_fails_without_consuming():
    _, _, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry, sequence=52, expires_after_sequence=51)

    result = _create(ledger, state, authorization, sequence=52)

    assert result.accepted is False
    assert result.reason == "diagnosis_authorization_expired"
    assert authorization.authorization_id not in result.state.consumed_diagnosis_authorization_ids


def test_consumed_authorization_fails_without_state_consumption():
    _, _, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry, consumed=True)

    result = _create(ledger, state, authorization)

    assert result.accepted is False
    assert result.reason == "diagnosis_authorization_consumed"
    assert authorization.authorization_id not in result.state.consumed_diagnosis_authorization_ids


def test_failed_authorization_attempts_remain_unconsumed():
    _, _, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry, operator_authority="DELTA_GENERATED")

    result = _create(ledger, state, authorization)

    assert result.accepted is False
    assert result.state == state
    assert result.state.consumed_diagnosis_authorization_ids == ()


def test_successful_one_shot_authorization_is_consumed_and_cannot_be_reused():
    _, _, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry)

    first = _create(ledger, state, authorization)
    second = _create(ledger, first.state, authorization)

    assert first.accepted is True
    assert authorization.authorization_id in first.state.consumed_diagnosis_authorization_ids
    assert second.accepted is False
    assert second.reason == "diagnosis_authorization_already_consumed"


def test_candidate_links_exact_ledger_entry_and_evidence_provenance():
    _, evidence, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry)

    result = _create(ledger, state, authorization)

    assert result.diagnosis is not None
    assert result.diagnosis.creation_authorization_id == authorization.authorization_id
    assert result.diagnosis.first_incorrect_transition == entry.first_incorrect_transition
    assert result.diagnosis.supporting_evidence == (result.evidence_references[0].evidence_reference_id,)
    assert result.evidence_references[0].deterministic_fingerprint == evidence.evidence_fingerprint
    assert result.evidence_references[0].live_runtime is True
    assert result.evidence_references[0].provider_or_model_derived is False


def test_candidate_remains_provisional_and_cannot_authorize_proposal_or_execution():
    _, _, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry)

    result = _create(ledger, state, authorization)

    assert result.diagnosis is not None
    assert result.diagnosis.provisional is True
    assert gsr.diagnosis_authorizes_proposal(result.diagnosis) is False
    assert gsr.diagnosis_candidate_creates_proposal(result.diagnosis) is False
    assert result.creates_repair_proposal is False
    assert all(value is False for value in result.diagnosis.safety.values())


def test_diagnosis_creation_performs_no_proposal_execution_or_persistence():
    _, _, _, ledger, entry = _eligible_ledger()
    state = gsr.make_diagnosis_proposal_state()
    authorization = _authorization(entry)

    result = _create(ledger, state, authorization)

    assert result.accepted is True
    assert result.state.repair_proposals == ()
    assert result.state.pending_proposal_review_queue == ()
    assert result.state.future_sandbox_planning_eligible_proposals == ()
    assert all(value is False for value in result.state.safety.values())
