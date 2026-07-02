from __future__ import annotations

import os

import pytest

from orchestration.runtime.runtime_reasoning import HYB1_ENV_FLAG, runtime_v13_hyb1_enabled
from orchestration.runtime.v14_candidate_envelope import (
    CandidateConfidence,
    CandidateProvenance,
    CandidateState,
    archive_candidate,
    create_candidate_envelope,
    transition_candidate,
    validate_transition,
)
from orchestration.runtime.v14_gap_map import build_original_delta_gap_map
from orchestration.runtime.v14_lanes import (
    LanePermission,
    RuntimeLane,
    allow_activation_only,
    block_planning_lane,
    block_reasoning_lane,
    can_use_in_lane,
)
from orchestration.runtime.v14_pruning import (
    CorrectiveAction,
    PruningFailureType,
    apply_pruning_projection,
    is_reversible_action,
    propose_pruning_record,
    should_require_human_review,
)
from orchestration.runtime.v14_signals import (
    ClaimPolarity,
    DecisionCriticality,
    EvidenceFunction,
    EvidenceRoleMetadata,
    SemanticSignalSet,
    empty_signal_set,
    is_strong_evidence_role,
    merge_signal_sets,
)


def test_all_new_modules_import_and_empty_signal_set_works():
    signal = empty_signal_set()

    assert signal.source == "empty"
    assert signal.evidence_role.evidence_function.value == "unknown"


def test_strong_evidence_role_detection_works():
    role = EvidenceRoleMetadata(
        evidence_function=EvidenceFunction.CAUSAL_EVIDENCE,
        claim_polarity=ClaimPolarity.SUPPORTS,
        decision_criticality=DecisionCriticality.ACTION_GUIDING,
        confidence=0.8,
    )

    assert is_strong_evidence_role(role)
    assert not is_strong_evidence_role(EvidenceRoleMetadata(confidence=1.0))


def test_merge_signal_sets_deduplicates_terms_and_keeps_highest_confidence_role():
    weak = SemanticSignalSet(
        evidence_role=EvidenceRoleMetadata(confidence=0.2),
        relation_terms=("cause", "cause"),
        source="weak",
    )
    strong = SemanticSignalSet(
        evidence_role=EvidenceRoleMetadata(
            evidence_function=EvidenceFunction.REVISION_EVIDENCE,
            claim_polarity=ClaimPolarity.QUALIFIES,
            decision_criticality=DecisionCriticality.ACTION_GUIDING,
            confidence=0.8,
        ),
        relation_terms=("cause", "revision"),
        action_terms=("revise",),
        source="strong",
    )

    merged = merge_signal_sets(weak, strong, source="test")

    assert merged.source == "test"
    assert merged.relation_terms == ("cause", "revision")
    assert merged.action_terms == ("revise",)
    assert merged.evidence_role.evidence_function == EvidenceFunction.REVISION_EVIDENCE


def test_lane_policy_can_allow_activation_but_block_reasoning():
    activation_only = allow_activation_only("concept-a", "diagnostic visibility only")

    assert can_use_in_lane(activation_only, RuntimeLane.ACTIVATION, LanePermission.VISIBLE)
    assert not can_use_in_lane(activation_only, RuntimeLane.REASONING)
    assert not can_use_in_lane(activation_only, RuntimeLane.EXECUTION)

    reasoning_blocked = block_reasoning_lane("concept-b", "same-topic noise in reasoning")
    assert can_use_in_lane(reasoning_blocked, RuntimeLane.ATTENTION, LanePermission.SELECTABLE)
    assert can_use_in_lane(reasoning_blocked, RuntimeLane.PLANNING, LanePermission.PLANNING_SUPPORT)
    assert not can_use_in_lane(reasoning_blocked, RuntimeLane.REASONING)

    planning_blocked = block_planning_lane("concept-c", "unsafe plan dependency")
    assert can_use_in_lane(planning_blocked, RuntimeLane.REASONING, LanePermission.CITABLE)
    assert not can_use_in_lane(planning_blocked, RuntimeLane.PLANNING)


@pytest.mark.parametrize(
    "action",
    [CorrectiveAction.DAMPEN, CorrectiveAction.REQUIRE_CONTEXT, CorrectiveAction.LANE_BLOCK],
)
def test_pruning_records_default_to_reversible_for_safe_actions(action: CorrectiveAction):
    record = propose_pruning_record(
        concept_id="concept-a",
        failure_context_hash="hash-123",
        failure_type=PruningFailureType.SAME_TOPIC_NOISE,
        affected_lane=RuntimeLane.REASONING,
        corrective_action=action,
    )

    assert is_reversible_action(record.corrective_action)
    assert record.decay_rule == "recover_after_successful_revalidation"


def test_quarantine_or_false_corrupt_concept_requires_human_review():
    assert should_require_human_review(
        PruningFailureType.FALSE_OR_CORRUPT_CONCEPT,
        CorrectiveAction.DAMPEN,
    )
    assert should_require_human_review(
        PruningFailureType.SAME_TOPIC_NOISE,
        CorrectiveAction.QUARANTINE,
    )


def test_apply_pruning_projection_does_not_mutate_input_object():
    state = block_reasoning_lane("concept-a", "baseline block")
    record = propose_pruning_record(
        concept_id="concept-a",
        failure_context_hash="hash-123",
        failure_type=PruningFailureType.REASONING_DRIFT,
        affected_lane=RuntimeLane.PLANNING,
        corrective_action=CorrectiveAction.LANE_BLOCK,
    )

    projected = apply_pruning_projection(state, record)

    assert projected is not state
    assert len(projected.policies) == len(state.policies) + 1
    assert state.policy_for(RuntimeLane.PLANNING).permission == LanePermission.PLANNING_SUPPORT
    assert projected.policy_for(RuntimeLane.PLANNING).permission == LanePermission.BLOCKED


def test_candidate_envelope_valid_transitions_and_archive_work():
    envelope = create_candidate_envelope(
        envelope_id="env-1",
        candidate_type="semantic_concept",
        payload={"text": "Evidence should match its runtime role."},
        provenance=CandidateProvenance(source="report-only"),
        confidence=CandidateConfidence(value=0.5),
    )

    assert validate_transition(CandidateState.GENERATED, CandidateState.VALIDATED)
    validated = transition_candidate(envelope, CandidateState.VALIDATED)
    queued = transition_candidate(validated, CandidateState.QUEUED_FOR_REPLAY)
    replayed = transition_candidate(queued, CandidateState.REPLAY_COMPLETED)
    reviewable = transition_candidate(replayed, CandidateState.ELIGIBLE_FOR_REVIEW)
    archived = archive_candidate(reviewable)

    assert envelope.state == CandidateState.GENERATED
    assert archived.state == CandidateState.ARCHIVED
    assert len(archived.decision_trace) > len(envelope.decision_trace)


def test_candidate_envelope_invalid_transitions_are_rejected():
    envelope = create_candidate_envelope(
        envelope_id="env-1",
        candidate_type="semantic_concept",
        payload={},
    )

    with pytest.raises(ValueError):
        transition_candidate(envelope, CandidateState.AUTHORIZED)


def test_gap_map_builds_and_includes_required_concepts():
    report = build_original_delta_gap_map()
    concepts = {item["concept"] for item in report["concept_statuses"]}

    assert report["report_only"] is True
    assert report["runtime_behavior_changed"] is False
    assert report["learning_changed"] is False
    assert report["storage_changed"] is False
    assert report["training_run"] is False
    assert report["final_recommendation"] == "PROCEED_OUTPUT_DISCIPLINE_SCAFFOLD"
    for required in {
        "evidence role metadata",
        "lane-specific permissions",
        "selective pruning / corrective dampening",
        "negative feedback memory",
        "CandidateEnvelope lifecycle",
        "replay-driven learning",
        "episodic-to-semantic consolidation",
        "live canonical memory store",
        "structural semantic adapter",
        "hypothesis arbitration",
        "confidence inertia / volatility",
        "internal rollout",
        "execution authorization",
        "DMSA/multi-stream assessment",
        "specialist routing",
        "unknown-answer output port",
        "controlled training",
    }:
        assert required in concepts


def test_model_b_default_behavior_is_not_changed_by_imports(monkeypatch):
    monkeypatch.delenv("DELTA_RUNTIME_V13_USAGE_GATE_MODE", raising=False)
    monkeypatch.delenv(HYB1_ENV_FLAG, raising=False)

    assert os.environ.get("DELTA_RUNTIME_V13_USAGE_GATE_MODE") is None
    assert runtime_v13_hyb1_enabled() is False
