from __future__ import annotations

import json

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_specialist_merge import (
    RUNTIME_V14J_INVARIANT_FLAGS,
    SpecialistClaimType,
    SpecialistEvidenceRelation,
    SpecialistMergeConflictType,
    SpecialistMergeOutcome,
    SpecialistPacketSource,
    create_specialist_evidence_link,
    create_specialist_evidence_packet,
    create_specialist_merge_conflict,
    create_specialist_merge_input,
    create_specialist_merge_plan,
    create_specialist_merge_report,
    create_specialist_result_claim,
    decide_specialist_merge,
    score_specialist_merge_input,
    validate_specialist_claim_inert,
    validate_specialist_merge_decision_report_only,
    validate_specialist_merge_input_inert,
    validate_specialist_merge_plan_inert,
    validate_specialist_merge_report_review_only,
    validate_specialist_packet_inert,
    validate_specialist_scorecard_report_only,
)
from orchestration.runtime.v14_specialist_merge_report import (
    build_specialist_merge_report_data,
    write_specialist_merge_report,
)


def _packet():
    return create_specialist_evidence_packet(
        specialist_name="mock_causal_specialist",
        packet_source=SpecialistPacketSource.MOCK_RESULT,
        source_reference_ids=("trace-1",),
        lane_scope=("reasoning",),
        summary="mock specialist evidence only",
    )


def _merge_input():
    packet = _packet()
    first = create_specialist_result_claim(
        packet_id=packet.packet_id,
        claim_text="Maintenance frequency should be evaluated with root-cause evidence.",
        claim_type=SpecialistClaimType.EVIDENCE_OBSERVATION,
        confidence_state=0.62,
        lane_scope=("planning",),
        provenance_reference_ids=("trace-1", "review-1"),
    )
    second = create_specialist_result_claim(
        packet_id=packet.packet_id,
        claim_text="The specialist answer should be accepted automatically.",
        claim_type=SpecialistClaimType.INTERPRETATION,
        confidence_state=0.4,
        lane_scope=("planning",),
        provenance_reference_ids=(),
    )
    links = (
        create_specialist_evidence_link(
            claim_id=first.claim_id,
            target_reference_id="candidate-1",
            evidence_relation=SpecialistEvidenceRelation.SUPPORTS,
            evidence_weight=0.85,
            rationale="supports root-cause planning evidence",
            provenance_reference_ids=("trace-1",),
        ),
        create_specialist_evidence_link(
            claim_id=second.claim_id,
            target_reference_id="candidate-2",
            evidence_relation=SpecialistEvidenceRelation.UNSAFE_TO_MERGE,
            evidence_weight=0.9,
            rationale="authority transfer risk",
            provenance_reference_ids=("trace-2",),
        ),
    )
    return create_specialist_merge_input(
        packets=(packet,),
        claims=(first, second),
        evidence_links=links,
        source_artifact_references=("specialist-packet-fixture",),
        lane_scope=("planning",),
    )


def test_importing_specialist_merge_does_not_change_defaults(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert runtime_v13_hyb1_enabled() is False
    assert all(value is False for value in RUNTIME_V14J_INVARIANT_FLAGS.values())


def test_specialist_packet_is_deterministic_and_inert():
    packet = _packet()
    duplicate = _packet()

    assert packet.packet_id == duplicate.packet_id
    assert packet.provider_call_performed is False
    assert packet.active_routing_used is False
    assert packet.authority_granted is False
    assert packet.canonical is False
    assert validate_specialist_packet_inert(packet)


def test_specialist_claim_is_not_truth_memory_or_learning():
    packet = _packet()
    claim = create_specialist_result_claim(
        packet_id=packet.packet_id,
        claim_text="A specialist result is evidence, not authority.",
        claim_type=SpecialistClaimType.SAFETY_NOTE,
        confidence_state=1.4,
        provenance_reference_ids=("trace-1",),
    )
    duplicate = create_specialist_result_claim(
        packet_id=packet.packet_id,
        claim_text=claim.claim_text,
        claim_type=claim.claim_type,
        confidence_state=claim.confidence_state,
        provenance_reference_ids=claim.provenance_reference_ids,
    )

    assert claim.claim_id == duplicate.claim_id
    assert claim.normalized_confidence() == 1.0
    assert claim.accepted_as_truth is False
    assert claim.learned is False
    assert claim.canonical is False
    assert validate_specialist_claim_inert(claim)


def test_specialist_evidence_link_is_deterministic_and_clamped():
    packet = _packet()
    claim = create_specialist_result_claim(packet_id=packet.packet_id, claim_text="Evidence should be bounded.")
    link = create_specialist_evidence_link(
        claim_id=claim.claim_id,
        target_reference_id="target-1",
        evidence_relation=SpecialistEvidenceRelation.WEAKLY_SUPPORTS,
        evidence_weight=-0.5,
        rationale="weak support",
    )
    duplicate = create_specialist_evidence_link(
        claim_id=claim.claim_id,
        target_reference_id="target-1",
        evidence_relation=SpecialistEvidenceRelation.WEAKLY_SUPPORTS,
        evidence_weight=-0.5,
        rationale="weak support",
    )

    assert link.link_id == duplicate.link_id
    assert link.normalized_weight() == 0.0


def test_specialist_merge_input_is_inert():
    merge_input = _merge_input()
    duplicate = create_specialist_merge_input(
        packets=merge_input.packets,
        claims=merge_input.claims,
        evidence_links=merge_input.evidence_links,
        source_artifact_references=merge_input.source_artifact_references,
        lane_scope=merge_input.lane_scope,
    )

    assert merge_input.merge_input_id == duplicate.merge_input_id
    assert merge_input.provider_calls_enabled is False
    assert merge_input.active_specialist_routing_enabled is False
    assert merge_input.authority_transfer_enabled is False
    assert validate_specialist_merge_input_inert(merge_input)


def test_specialist_merge_conflict_is_unresolved_report_material():
    merge_input = _merge_input()
    conflict = create_specialist_merge_conflict(
        packet_ids=(merge_input.packets[0].packet_id,),
        claim_ids=(merge_input.claims[1].claim_id, merge_input.claims[0].claim_id),
        conflict_type=SpecialistMergeConflictType.AUTHORITY_RISK,
        rationale="authority transfer would be unsafe",
        requires_human_review=True,
    )
    duplicate = create_specialist_merge_conflict(
        packet_ids=(merge_input.packets[0].packet_id,),
        claim_ids=(merge_input.claims[0].claim_id, merge_input.claims[1].claim_id),
        conflict_type=SpecialistMergeConflictType.AUTHORITY_RISK,
        rationale="authority transfer would be unsafe",
        requires_human_review=True,
    )

    assert conflict.conflict_id == duplicate.conflict_id
    assert conflict.resolved is False
    assert conflict.requires_human_review is True


def test_specialist_merge_scorecards_are_report_only():
    merge_input = _merge_input()
    scorecards = score_specialist_merge_input(merge_input)

    assert len(scorecards) == 2
    assert all(validate_specialist_scorecard_report_only(scorecard) for scorecard in scorecards)
    assert all(scorecard.authoritative is False for scorecard in scorecards)
    assert max(scorecard.merge_readiness_score for scorecard in scorecards) > 0


def test_specialist_merge_decision_is_report_only_candidate_not_authority():
    merge_input = _merge_input()
    scorecards = score_specialist_merge_input(merge_input)
    decision = decide_specialist_merge(merge_input, scorecards)

    assert decision.outcome == SpecialistMergeOutcome.REPORT_ONLY_MERGE_CANDIDATE
    assert decision.merge_candidate_claim_ids
    assert decision.applied is False
    assert decision.authoritative is False
    assert decision.provider_called is False
    assert "not truth or authority" in decision.rationale
    assert validate_specialist_merge_decision_report_only(decision)


def test_specialist_merge_decision_can_require_human_or_replay_review():
    merge_input = _merge_input()
    scorecards = score_specialist_merge_input(merge_input)
    human_conflict = create_specialist_merge_conflict(
        packet_ids=(merge_input.packets[0].packet_id,),
        claim_ids=(merge_input.claims[0].claim_id,),
        conflict_type=SpecialistMergeConflictType.SAFETY_CONFLICT,
        requires_human_review=True,
    )
    human_decision = decide_specialist_merge(merge_input, scorecards, conflicts=(human_conflict,))
    assert human_decision.outcome == SpecialistMergeOutcome.REQUIRES_HUMAN_REVIEW

    replay_conflict = create_specialist_merge_conflict(
        packet_ids=(merge_input.packets[0].packet_id,),
        claim_ids=(merge_input.claims[0].claim_id,),
        conflict_type=SpecialistMergeConflictType.CLAIM_CONTRADICTION,
        requires_replay_review=True,
    )
    replay_decision = decide_specialist_merge(merge_input, scorecards, conflicts=(replay_conflict,))
    assert replay_decision.outcome == SpecialistMergeOutcome.REQUIRES_REPLAY_REVIEW


def test_specialist_merge_report_is_review_only():
    merge_input = _merge_input()
    scorecards = score_specialist_merge_input(merge_input)
    decision = decide_specialist_merge(merge_input, scorecards)
    report = create_specialist_merge_report(
        merge_input,
        scorecards,
        decision,
        evidence_gaps=("no live provider call was made",),
    )

    assert report.generated_for_review_only is True
    assert report.decision.applied is False
    assert report.evidence_gaps == ("no live provider call was made",)
    assert validate_specialist_merge_report_review_only(report)


def test_specialist_merge_plan_has_no_provider_or_authority_path():
    merge_input = _merge_input()
    decision = decide_specialist_merge(merge_input, score_specialist_merge_input(merge_input))
    plan = create_specialist_merge_plan(merge_inputs=(merge_input,), decisions=(decision,))

    assert plan.merge_input_ids == (merge_input.merge_input_id,)
    assert plan.provider_calls_enabled is False
    assert plan.active_specialist_routing_enabled is False
    assert plan.authority_transfer_enabled is False
    assert plan.canonical_write_enabled is False
    assert plan.memory_mutation_enabled is False
    assert plan.training_enabled is False
    assert validate_specialist_merge_plan_inert(plan)


def test_specialist_merge_report_data_states_dormant_non_authoritative_status():
    data = build_specialist_merge_report_data()

    assert data["final_recommendation"] == "PROCEED_RECALL_BRIDGE_DESIGN"
    assert data["safety_boundaries"]["provider_calls_enabled"] is False
    assert data["safety_boundaries"]["active_specialist_routing_enabled"] is False
    assert data["safety_boundaries"]["authority_transfer_enabled"] is False
    assert data["inactive_systems"]["canonical_memory_mutation"] is False


def test_write_specialist_merge_report_creates_md_and_json(tmp_path):
    md_path = tmp_path / "runtime_v14j_dormant_specialist_merge_protocol_design.md"
    json_path = tmp_path / "runtime_v14j_dormant_specialist_merge_protocol_design.json"

    write_specialist_merge_report(md_path, json_path)

    assert md_path.exists()
    assert json_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    text = md_path.read_text(encoding="utf-8")
    assert data["final_recommendation"] == "PROCEED_RECALL_BRIDGE_DESIGN"
    assert "specialist result != truth" in text
    assert "A merge candidate is not truth" in text
