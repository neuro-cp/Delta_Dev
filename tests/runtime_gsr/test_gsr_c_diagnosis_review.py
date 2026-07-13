from __future__ import annotations

from orchestration.runtime import gsr_a_governed_self_regulation as gsr


def _gate_a_candidate():
    objective = gsr.make_development_objective("Review provisional diagnosis.", sequence=60)
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
        sequence=60,
        user_visible=True,
        live_runtime=True,
        evidence_fingerprint="diagnosis-review-evidence",
    )
    observation = gsr.make_observation(
        objective.objective_id,
        source_subsystem=evidence.source_subsystem,
        observed_behavior=evidence.observed_transition,
        expected_behavior=evidence.expected_transition,
        evidence_references=(evidence.evidence_id,),
        confidence=0.72,
        uncertainty="operator_transcript",
        reproducibility="single_sequence",
        user_visible=True,
    )
    ledger = gsr.make_observation_ledger(objective.objective_id, sequence=60)
    recorded = gsr.record_observation(ledger, observation, evidence)
    assert recorded.entry is not None
    review = gsr.make_observation_review_decision(
        recorded.entry.ledger_entry_id,
        decision="approve",
        allowed_transition="diagnosis_review_eligible",
        rationale="operator marks entry eligible",
        sequence=61,
    )
    eligible = gsr.review_observation_entry(recorded.state, review)
    assert eligible.entry is not None
    authorization = gsr.make_diagnosis_review_authorization(
        eligible.entry.ledger_entry_id,
        allowed_diagnosis_scope=("first_incorrect_transition", "mechanism"),
        linked_objective_id=objective.objective_id,
        decision_sequence=62,
    )
    state = gsr.make_diagnosis_proposal_state()
    result = gsr.create_provisional_diagnosis_candidate(
        eligible.state,
        state,
        authorization,
        suspected_mechanism="pending local-model action consumes discourse recall",
        competing_hypotheses=("pending action precedence", "concept recall fallback"),
        confidence=0.66,
        uncertainty="provisional",
        severity="medium",
        reproducibility="single_sequence",
        scope_estimate="bounded",
        affected_components=("DELTA._send_chat",),
        forbidden_components=("provider_runtime", "sandbox_execution"),
        sequence=62,
    )
    assert result.diagnosis is not None
    return result.state, result.diagnosis, result.evidence_references[0]


def test_b1_multiple_hypotheses_remain_separately_reviewable():
    state, diagnosis, _ = _gate_a_candidate()
    pending = gsr.make_competing_diagnosis_hypothesis(
        diagnosis,
        mechanism_description="pending action precedence",
        confidence=0.9,
        sequence=70,
    )
    recall = gsr.make_competing_diagnosis_hypothesis(
        diagnosis,
        mechanism_description="concept recall fallback",
        confidence=0.2,
        sequence=71,
    )

    with_first = gsr.add_competing_diagnosis_hypothesis(state, diagnosis, pending)
    with_both = gsr.add_competing_diagnosis_hypothesis(with_first, diagnosis, recall)

    assert len(with_both.competing_hypotheses) == 2
    assert {item["mechanism_description"] for item in with_both.competing_hypotheses} == {
        "pending action precedence",
        "concept recall fallback",
    }
    assert gsr.diagnosis_has_automatic_hypothesis_winner(with_both, diagnosis.diagnosis_id) is False


def test_b1_supporting_disconfirming_neutral_and_unresolved_evidence_stay_separate():
    _, diagnosis, evidence_ref = _gate_a_candidate()
    hypothesis = gsr.make_competing_diagnosis_hypothesis(
        diagnosis,
        mechanism_description="pending action precedence",
        sequence=70,
    )

    supporting = gsr.attach_evidence_to_hypothesis(hypothesis, evidence_ref, role="supporting", sequence=71)
    disconfirming = gsr.attach_evidence_to_hypothesis(supporting, evidence_ref, role="disconfirming", sequence=72)
    neutral = gsr.attach_evidence_to_hypothesis(disconfirming, evidence_ref, role="neutral", sequence=73)
    unresolved = gsr.attach_evidence_to_hypothesis(neutral, evidence_ref, role="unresolved", sequence=74)

    assert unresolved.supporting_evidence_reference_ids == (evidence_ref.evidence_reference_id,)
    assert unresolved.disconfirming_evidence_reference_ids == (evidence_ref.evidence_reference_id,)
    assert unresolved.neutral_evidence_reference_ids == (evidence_ref.evidence_reference_id,)
    assert unresolved.unresolved_evidence_reference_ids == (evidence_ref.evidence_reference_id,)


def test_b1_confidence_severity_and_reproducibility_do_not_select_winner():
    state, diagnosis, _ = _gate_a_candidate()
    strong = gsr.make_competing_diagnosis_hypothesis(
        diagnosis,
        mechanism_description="strong but still provisional",
        confidence=0.99,
        sequence=70,
    )
    state = gsr.add_competing_diagnosis_hypothesis(state, diagnosis, strong)
    high_signal = gsr.DiagnosisCandidate(**{
        **gsr.serialize(diagnosis),
        "confidence": 0.99,
        "severity": "critical",
        "reproducibility": "high",
    })

    assert high_signal.operator_review_status == "pending_review"
    assert high_signal.provisional is True
    assert gsr.diagnosis_has_automatic_hypothesis_winner(state, diagnosis.diagnosis_id) is False


def test_b1_hypothesis_cannot_select_itself_and_invalid_role_is_ignored():
    _, diagnosis, evidence_ref = _gate_a_candidate()
    hypothesis = gsr.make_competing_diagnosis_hypothesis(
        diagnosis,
        mechanism_description="pending action precedence",
        sequence=70,
    )

    unchanged = gsr.attach_evidence_to_hypothesis(hypothesis, evidence_ref, role="winner", sequence=71)

    assert unchanged == hypothesis
    assert gsr.hypothesis_selects_itself(hypothesis) is False


def test_b1_foreign_hypothesis_is_not_added_to_state():
    state, diagnosis, _ = _gate_a_candidate()
    other = gsr.DiagnosisCandidate(**{**gsr.serialize(diagnosis), "diagnosis_id": "other-diagnosis"})
    foreign = gsr.make_competing_diagnosis_hypothesis(
        other,
        mechanism_description="foreign hypothesis",
        sequence=70,
    )

    unchanged = gsr.add_competing_diagnosis_hypothesis(state, diagnosis, foreign)

    assert unchanged == state


def _state_with_two_hypotheses():
    state, diagnosis, evidence_ref = _gate_a_candidate()
    first = gsr.make_competing_diagnosis_hypothesis(
        diagnosis,
        mechanism_description="pending action precedence",
        sequence=70,
    )
    second = gsr.make_competing_diagnosis_hypothesis(
        diagnosis,
        mechanism_description="concept recall fallback",
        sequence=71,
    )
    state = gsr.add_competing_diagnosis_hypothesis(state, diagnosis, first)
    state = gsr.add_competing_diagnosis_hypothesis(state, diagnosis, second)
    return state, diagnosis, evidence_ref, first, second


def test_b2_candidate_cannot_review_itself_and_non_operator_decision_fails():
    state, diagnosis, _, first, _ = _state_with_two_hypotheses()
    self_signed = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="revise",
        selected_hypothesis_id=first.hypothesis_id,
        rationale="candidate cannot sign its own review",
        allowed_next_transition="diagnosis_revision_required",
        operator_authority=diagnosis.diagnosis_id,
        decision_sequence=80,
    )
    non_operator = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="revise",
        selected_hypothesis_id=first.hypothesis_id,
        rationale="DELTA-generated decision must fail",
        allowed_next_transition="diagnosis_revision_required",
        operator_authority="DELTA_GENERATED",
        decision_sequence=81,
    )

    self_result = gsr.review_diagnosis_candidate(state, self_signed, sequence=80)
    non_operator_result = gsr.review_diagnosis_candidate(state, non_operator, sequence=81)

    assert gsr.diagnosis_candidate_can_review_itself(diagnosis) is False
    assert self_result.accepted is False
    assert self_result.reason == "operator_authority_required"
    assert non_operator_result.accepted is False
    assert non_operator_result.reason == "operator_authority_required"
    assert self_signed.decision_id not in self_result.state.consumed_diagnosis_decision_ids
    assert non_operator.decision_id not in non_operator_result.state.consumed_diagnosis_decision_ids


def test_b2_wrong_target_and_foreign_hypothesis_fail_without_consuming():
    state, diagnosis, _, first, _ = _state_with_two_hypotheses()
    wrong_target = gsr.make_diagnosis_review_decision(
        "missing-diagnosis",
        disposition="revise",
        rationale="wrong target",
        allowed_next_transition="diagnosis_revision_required",
        decision_sequence=80,
    )
    foreign = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="revise",
        selected_hypothesis_id="foreign-hypothesis",
        rationale="foreign hypothesis",
        allowed_next_transition="diagnosis_revision_required",
        decision_sequence=81,
    )

    wrong_result = gsr.review_diagnosis_candidate(state, wrong_target, sequence=80)
    foreign_result = gsr.review_diagnosis_candidate(state, foreign, sequence=81)

    assert wrong_result.accepted is False
    assert wrong_result.reason == "diagnosis_not_found"
    assert wrong_target.decision_id not in wrong_result.state.consumed_diagnosis_decision_ids
    assert foreign_result.accepted is False
    assert foreign_result.reason == "selected_hypothesis_not_in_diagnosis"
    assert first.hypothesis_id != "foreign-hypothesis"


def test_b2_expired_and_consumed_decisions_fail_without_consuming_state():
    state, diagnosis, _, first, _ = _state_with_two_hypotheses()
    expired = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="revise",
        selected_hypothesis_id=first.hypothesis_id,
        rationale="expired",
        allowed_next_transition="diagnosis_revision_required",
        decision_sequence=80,
        expires_after_sequence=79,
    )
    consumed = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="revise",
        selected_hypothesis_id=first.hypothesis_id,
        rationale="already consumed",
        allowed_next_transition="diagnosis_revision_required",
        decision_sequence=81,
        consumed=True,
    )

    expired_result = gsr.review_diagnosis_candidate(state, expired, sequence=80)
    consumed_result = gsr.review_diagnosis_candidate(state, consumed, sequence=81)

    assert expired_result.accepted is False
    assert expired_result.reason == "diagnosis_review_decision_expired"
    assert consumed_result.accepted is False
    assert consumed_result.reason == "diagnosis_review_decision_consumed"
    assert expired_result.state.consumed_diagnosis_decision_ids == ()
    assert consumed_result.state.consumed_diagnosis_decision_ids == ()


def test_b2_successful_one_shot_review_decision_is_consumed_and_reuse_fails():
    state, diagnosis, _, first, _ = _state_with_two_hypotheses()
    decision = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="revise",
        selected_hypothesis_id=first.hypothesis_id,
        rationale="operator requests diagnosis revision",
        allowed_next_transition="diagnosis_revision_required",
        decision_sequence=80,
    )

    first_result = gsr.review_diagnosis_candidate(state, decision, sequence=80)
    second_result = gsr.review_diagnosis_candidate(first_result.state, decision, sequence=81)

    assert first_result.accepted is True
    assert first_result.diagnosis is not None
    assert first_result.diagnosis.operator_review_status == "revise"
    assert decision.decision_id in first_result.state.consumed_diagnosis_decision_ids
    assert second_result.accepted is False
    assert second_result.reason == "diagnosis_review_decision_already_consumed"
    assert first_result.creates_repair_proposal is False


def test_b2_unknown_disposition_fails_closed():
    state, diagnosis, _, first, _ = _state_with_two_hypotheses()
    decision = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition="auto_accept",
        selected_hypothesis_id=first.hypothesis_id,
        rationale="unknown disposition",
        allowed_next_transition="automatic",
        decision_sequence=80,
    )

    result = gsr.review_diagnosis_candidate(state, decision, sequence=80)

    assert result.accepted is False
    assert result.reason == "unknown_diagnosis_disposition"
    assert decision.decision_id not in result.state.consumed_diagnosis_decision_ids


def _review_with_disposition(disposition: str):
    state, diagnosis, _, first, _ = _state_with_two_hypotheses()
    decision = gsr.make_diagnosis_review_decision(
        diagnosis.diagnosis_id,
        disposition=disposition,
        selected_hypothesis_id=first.hypothesis_id,
        rationale=f"operator marks {disposition}",
        allowed_next_transition=disposition,
        decision_sequence=90,
    )
    return diagnosis, decision, gsr.review_diagnosis_candidate(state, decision, sequence=90)


def test_b3_blocking_dispositions_do_not_enable_proposal_drafting():
    blocked = {
        "rejected": "rejected_diagnoses",
        "non_defect": "non_defect_diagnoses",
        "insufficient_evidence": "insufficient_evidence_diagnoses",
        "suspended": "suspended_diagnoses",
        "expired": "expired_diagnoses",
        "duplicate_diagnosis": "duplicate_diagnoses",
        "competing_hypothesis_unresolved": "unresolved_diagnoses",
        "deeper_design_required": "deeper_design_diagnoses",
    }
    for disposition, index_name in blocked.items():
        diagnosis, _, result = _review_with_disposition(disposition)

        assert result.accepted is True
        assert gsr.diagnosis_disposition_blocks_proposal_drafting(disposition) is True
        assert gsr.diagnosis_is_eligible_for_proposal_drafting(result.state, diagnosis.diagnosis_id) is False
        assert diagnosis.diagnosis_id in getattr(result.state, index_name)
        assert result.state.repair_proposals == ()
        assert result.creates_repair_proposal is False


def test_b3_accepted_for_proposal_drafting_adds_only_eligibility_marker():
    diagnosis, decision, result = _review_with_disposition("accepted_for_proposal_drafting")

    assert result.accepted is True
    assert decision.decision_id in result.state.consumed_diagnosis_decision_ids
    assert gsr.diagnosis_is_eligible_for_proposal_drafting(result.state, diagnosis.diagnosis_id) is True
    assert result.state.proposal_drafting_eligible_diagnoses == (diagnosis.diagnosis_id,)
    assert result.state.repair_proposals == ()
    assert result.state.pending_proposal_review_queue == ()
    assert result.state.future_sandbox_planning_eligible_proposals == ()
    assert result.creates_repair_proposal is False


def test_b3_accepted_diagnosis_creates_no_sandbox_patch_execution_or_source_mutation():
    _, _, result = _review_with_disposition("accepted_for_proposal_drafting")

    assert result.state.repair_proposals == ()
    assert result.state.proposal_review_decisions == ()
    assert result.state.future_sandbox_planning_eligible_proposals == ()
    assert all(value is False for value in result.state.safety.values())
    assert result.creates_repair_proposal is False


def test_b3_serialization_preserves_disposition_indexes_and_consumed_decision_ids():
    import json

    diagnosis, decision, result = _review_with_disposition("deeper_design_required")
    restored = gsr.deserialize(gsr.DiagnosisProposalState, json.loads(json.dumps(gsr.serialize(result.state))))

    assert diagnosis.diagnosis_id in restored.deeper_design_diagnoses
    assert decision.decision_id in restored.consumed_diagnosis_decision_ids
    assert restored.repair_proposals == ()
    repeat = gsr.review_diagnosis_candidate(restored, decision, sequence=91)
    assert repeat.accepted is False
    assert repeat.reason == "diagnosis_review_decision_already_consumed"


def test_b3_revision_does_not_enable_proposal_drafting():
    diagnosis, _, result = _review_with_disposition("revise")

    assert result.accepted is True
    assert gsr.diagnosis_is_eligible_for_proposal_drafting(result.state, diagnosis.diagnosis_id) is False
    assert result.state.repair_proposals == ()
