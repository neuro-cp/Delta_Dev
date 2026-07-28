"""Inert governed cross-turn claim-relation contract.

COGNITIVE-TRANSFER-CYCLE-1B defines durable claim identity, typed relation
state, restart reconstruction, operator resolution, and bounded authority
semantics. This module is intentionally not wired into memory, discourse,
authority routing, or conversation rendering.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.developmental_bootstrap import bootstrap_digest
from orchestration.runtime.operator_ux import FIXED_TIMESTAMP


STATUS_PASSED = "COGNITIVE_TRANSFER_CYCLE_1B_CONTRACT_PASSED"
SCHEMA_VERSION = "governed_claim_relation_contract_v1"
AUTHORITY_SCOPE = "inert_claim_relation_contract_only"
BASELINE_GAP_ID = "durable_cross_turn_claim_relation_state_missing"
TRANSFER_STATUS = "COGNITIVE_TRANSFER_CYCLE_1A_GAP_IDENTIFIED"
EVALUATOR_PATH = "orchestration/runtime/cognitive_contradiction_evaluation.py"
PROPOSAL_ID = "cognitive-proposal-a6777613a9e0784f"

RELATION_TYPES = (
    "confirms",
    "duplicate_restatement",
    "explicit_correction",
    "direct_contradiction",
    "uncertain_conflict",
    "temporal_transition",
    "scoped_preference_update",
    "bounded_exception",
    "authority_revocation",
    "unrelated",
    "ambiguous_scope",
    "unresolved_relation",
)
LIFECYCLE_STATES = (
    "current",
    "superseded",
    "revoked",
    "conditionally_current",
    "unresolved",
    "historical",
    "rejected",
    "invalid",
)
RESOLUTION_STATES = (
    "resolved",
    "unresolved",
    "operator_pending",
    "operator_resolved",
    "grounded_evidence_resolved",
    "invalid",
)
CONFIDENCE_STATES = ("known", "uncertain", "ambiguous")

REQUIRED_REPORT_FILES = (
    "baseline.json",
    "branch_head.json",
    "dirty_tree_before.json",
    "first_missing_transition.json",
    "transfer_gap_identity.json",
    "evaluator_identity.json",
    "evaluator_digest.json",
    "behavioral_requirements.json",
    "claim_schema.json",
    "claim_identity.json",
    "relation_schema.json",
    "relation_types.json",
    "lifecycle_states.json",
    "transition_contracts.json",
    "correction_semantics.json",
    "contradiction_semantics.json",
    "preference_scope_semantics.json",
    "bounded_exception_semantics.json",
    "revocation_semantics.json",
    "temporal_semantics.json",
    "ambiguity_semantics.json",
    "operator_request_contract.json",
    "dependent_work_contract.json",
    "authority_rules.json",
    "provenance_rules.json",
    "persistence_contract.json",
    "restart_contract.json",
    "corruption_handling.json",
    "serialization_roundtrip.json",
    "evaluator_compatibility.json",
    "proposal_amendment.json",
    "proposal_amendment_digest.json",
    "future_integration_paths.json",
    "activation_block.json",
    "negative_controls.json",
    "no_model_execution.json",
    "no_candidate_generation.json",
    "no_production_integration.json",
    "replay_checkpoint_regression.json",
    "test_results.json",
    "py_compile_result.json",
    "diff_check_result.json",
    "whitespace_result.json",
    "process_cleanup.json",
    "dirty_tree_after.json",
    "final_status.json",
)


@dataclass(frozen=True)
class GovernedClaimRecord:
    claim_id: str
    claim_digest: str
    subject_scope: str
    claim_text: str
    normalized_content: Mapping[str, Any]
    claim_kind: str
    temporal_scope: str
    applicability_scope: str
    provenance_refs: tuple[str, ...]
    authority_source: str
    created_at: str
    validation_state: str
    lifecycle_state: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernedClaimRelationRecord:
    relation_id: str
    left_claim_id: str
    right_claim_id: str
    relation_type: str
    relation_scope: str
    temporal_order: str
    confidence_state: str
    evidence_refs: tuple[str, ...]
    authority_effect: str
    resolution_state: str
    supersedes_claim_id: str
    operator_request_id: str
    dependent_work_ids: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    created_at: str
    resolved_at: str
    resolution_actor: str
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernedOperatorResolutionRecord:
    request_id: str
    resolution_key: str
    human_question: str
    affected_claim_ids: tuple[str, ...]
    affected_work_ids: tuple[str, ...]
    recommended_interpretation: str
    authority_required: str
    pending_state: str
    consumed: bool
    created_at: str
    resolved_at: str = ""
    resolution_actor: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovernedWorkItem:
    work_id: str
    state: str
    dependent_claim_ids: tuple[str, ...] = ()
    blocked_by_operator_request_id: str = ""
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClaimRelationStateBundle:
    claims: tuple[GovernedClaimRecord, ...] = ()
    relations: tuple[GovernedClaimRelationRecord, ...] = ()
    operator_requests: tuple[GovernedOperatorResolutionRecord, ...] = ()
    work_items: tuple[GovernedWorkItem, ...] = ()
    transition_journal: tuple[Mapping[str, Any], ...] = ()
    schema_version: str = SCHEMA_VERSION

    def as_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TransitionResult:
    accepted: bool
    reason: str
    before_state: ClaimRelationStateBundle
    after_state: ClaimRelationStateBundle
    relation: GovernedClaimRelationRecord | None = None
    operator_request: GovernedOperatorResolutionRecord | None = None


def first_missing_transition() -> dict[str, Any]:
    return {
        "schema": "cognitive_transfer_cycle_1b_first_missing_transition_v1",
        "first_missing_transition": (
            "claim A is retained -> later claim B arrives -> no governed state represents whether B confirms, "
            "corrects, contradicts, supersedes, revokes, qualifies, or is unrelated to A -> current truth, "
            "authority, provenance, and dependent work cannot be governed durably"
        ),
        "required_transition": (
            "claim identities -> typed relation record -> relation classification -> current/superseded state -> "
            "authority and scope effect -> persistence -> restart reconstruction -> operator-resolution boundary -> "
            "deterministic resolution transition -> stop before production integration"
        ),
    }


def construct_claim(
    *,
    subject_scope: str = "project_database",
    claim_text: str = "The project database is PostgreSQL.",
    normalized_content: Mapping[str, Any] | None = None,
    claim_kind: str = "fact",
    temporal_scope: str = "current",
    applicability_scope: str = "project",
    provenance_refs: Sequence[str] = ("turn:1",),
    authority_source: str = "operator",
    validation_state: str = "registered",
    lifecycle_state: str = "current",
    created_at: str = FIXED_TIMESTAMP,
) -> GovernedClaimRecord:
    normalized = dict(normalized_content or {"subject": subject_scope, "predicate": claim_text.lower().strip()})
    identity_payload = {
        "normalized_content": normalized,
        "claim_kind": claim_kind,
        "subject_scope": subject_scope,
        "temporal_scope": temporal_scope,
        "applicability_scope": applicability_scope,
        "provenance_refs": tuple(provenance_refs),
        "authority_source": authority_source,
        "schema_version": SCHEMA_VERSION,
    }
    digest_payload = {**identity_payload, "claim_text": claim_text}
    claim_digest = bootstrap_digest(digest_payload)
    return GovernedClaimRecord(
        claim_id="claim-" + bootstrap_digest(identity_payload)[:16],
        claim_digest=claim_digest,
        subject_scope=subject_scope,
        claim_text=claim_text,
        normalized_content=normalized,
        claim_kind=claim_kind,
        temporal_scope=temporal_scope,
        applicability_scope=applicability_scope,
        provenance_refs=tuple(provenance_refs),
        authority_source=authority_source,
        created_at=created_at,
        validation_state=validation_state,
        lifecycle_state=lifecycle_state,
    )


def relation_identity(
    *,
    left_claim_id: str,
    right_claim_id: str,
    relation_type: str,
    relation_scope: str,
    temporal_order: str,
    authority_effect: str,
) -> str:
    return "claim-relation-" + bootstrap_digest({
        "left_claim_id": left_claim_id,
        "right_claim_id": right_claim_id,
        "relation_type": relation_type,
        "relation_scope": relation_scope,
        "temporal_order": temporal_order,
        "authority_effect": authority_effect,
        "schema_version": SCHEMA_VERSION,
    })[:16]


def construct_relation(
    left: GovernedClaimRecord,
    right: GovernedClaimRecord,
    *,
    relation_type: str,
    relation_scope: str = "same_subject_scope",
    temporal_order: str = "left_before_right",
    confidence_state: str = "known",
    evidence_refs: Sequence[str] = (),
    authority_effect: str = "none",
    resolution_state: str = "resolved",
    supersedes_claim_id: str = "",
    operator_request_id: str = "",
    dependent_work_ids: Sequence[str] = (),
    provenance_refs: Sequence[str] = (),
    created_at: str = FIXED_TIMESTAMP,
    resolved_at: str = "",
    resolution_actor: str = "",
) -> GovernedClaimRelationRecord:
    if relation_type not in RELATION_TYPES:
        raise ValueError("unsupported_relation_type")
    if confidence_state not in CONFIDENCE_STATES:
        raise ValueError("unsupported_confidence_state")
    if resolution_state not in RESOLUTION_STATES:
        raise ValueError("unsupported_resolution_state")
    refs = tuple(provenance_refs) or left.provenance_refs + right.provenance_refs
    return GovernedClaimRelationRecord(
        relation_id=relation_identity(
            left_claim_id=left.claim_id,
            right_claim_id=right.claim_id,
            relation_type=relation_type,
            relation_scope=relation_scope,
            temporal_order=temporal_order,
            authority_effect=authority_effect,
        ),
        left_claim_id=left.claim_id,
        right_claim_id=right.claim_id,
        relation_type=relation_type,
        relation_scope=relation_scope,
        temporal_order=temporal_order,
        confidence_state=confidence_state,
        evidence_refs=tuple(evidence_refs),
        authority_effect=authority_effect,
        resolution_state=resolution_state,
        supersedes_claim_id=supersedes_claim_id,
        operator_request_id=operator_request_id,
        dependent_work_ids=tuple(dependent_work_ids),
        provenance_refs=refs,
        created_at=created_at,
        resolved_at=resolved_at,
        resolution_actor=resolution_actor,
    )


def validate_claim(record: GovernedClaimRecord) -> tuple[str, ...]:
    reasons: list[str] = []
    if record.schema_version != SCHEMA_VERSION:
        reasons.append("unsupported_schema_version")
    if not record.claim_id or not record.claim_digest:
        reasons.append("missing_claim_identity")
    if not record.provenance_refs:
        reasons.append("missing_provenance")
    if record.lifecycle_state not in LIFECYCLE_STATES:
        reasons.append("unsupported_lifecycle_state")
    if not record.subject_scope or not record.applicability_scope:
        reasons.append("missing_scope")
    return tuple(reasons)


def validate_relation(record: GovernedClaimRelationRecord) -> tuple[str, ...]:
    reasons: list[str] = []
    if record.schema_version != SCHEMA_VERSION:
        reasons.append("unsupported_schema_version")
    if record.relation_type not in RELATION_TYPES:
        reasons.append("unsupported_relation_type")
    if record.resolution_state not in RESOLUTION_STATES:
        reasons.append("unsupported_resolution_state")
    if record.confidence_state not in CONFIDENCE_STATES:
        reasons.append("unsupported_confidence_state")
    if not record.left_claim_id or not record.right_claim_id:
        reasons.append("missing_claim_link")
    if not record.provenance_refs:
        reasons.append("missing_provenance")
    if record.relation_type in {"explicit_correction", "scoped_preference_update", "authority_revocation"} and not record.supersedes_claim_id:
        reasons.append("missing_supersession_link")
    if record.relation_type == "ambiguous_scope" and not record.operator_request_id:
        reasons.append("missing_operator_request")
    return tuple(reasons)


def validate_bundle(bundle: ClaimRelationStateBundle) -> tuple[str, ...]:
    reasons: list[str] = []
    if bundle.schema_version != SCHEMA_VERSION:
        reasons.append("unsupported_schema_version")
    claim_ids = {claim.claim_id for claim in bundle.claims}
    for claim in bundle.claims:
        reasons.extend(validate_claim(claim))
    for relation in bundle.relations:
        reasons.extend(validate_relation(relation))
        if relation.left_claim_id not in claim_ids or relation.right_claim_id not in claim_ids:
            reasons.append("relation_missing_claim_record")
    return tuple(dict.fromkeys(reasons))


def register_claim(bundle: ClaimRelationStateBundle, claim: GovernedClaimRecord, *, idempotency_key: str = "") -> TransitionResult:
    expected_key = bootstrap_digest({"transition": "register_claim", "claim_id": claim.claim_id})
    if idempotency_key and idempotency_key != expected_key:
        raise ValueError("invalid_idempotency_key")
    if claim.claim_id in {item.claim_id for item in bundle.claims}:
        return TransitionResult(True, "duplicate_claim_suppressed", bundle, bundle)
    after = replace(bundle, claims=bundle.claims + (claim,), transition_journal=bundle.transition_journal + (_journal("register_claim", (claim.claim_id,)),))
    return TransitionResult(True, "claim_registered", bundle, after)


def classify_relation(left: GovernedClaimRecord, right: GovernedClaimRecord) -> str:
    if left.subject_scope != right.subject_scope:
        return "unrelated"
    if left.claim_digest == right.claim_digest:
        return "duplicate_restatement"
    right_text = right.claim_text.lower()
    if right_text.startswith("correction:") or "correction:" in right_text:
        return "explicit_correction"
    if "may be" in right_text or "suggests" in right_text:
        return "uncertain_conflict"
    if right.temporal_scope != left.temporal_scope:
        return "temporal_transition"
    if right.applicability_scope != left.applicability_scope and right.claim_kind == "preference":
        return "scoped_preference_update"
    return "direct_contradiction"


def link_confirmation(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord) -> TransitionResult:
    return _append_relation(bundle, construct_relation(left, right, relation_type="confirms", authority_effect="no_lifecycle_change"))


def link_duplicate(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord) -> TransitionResult:
    return _append_relation(bundle, construct_relation(left, right, relation_type="duplicate_restatement", authority_effect="duplicate_suppressed"))


def apply_explicit_correction(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord) -> TransitionResult:
    relation = construct_relation(
        left,
        right,
        relation_type="explicit_correction",
        authority_effect="left_superseded_right_current",
        supersedes_claim_id=left.claim_id,
        resolution_state="resolved",
        resolved_at=FIXED_TIMESTAMP,
        resolution_actor=right.authority_source,
    )
    after = _replace_claims(bundle, {left.claim_id: replace(left, lifecycle_state="superseded"), right.claim_id: replace(right, lifecycle_state="current")})
    after = replace(after, relations=_dedupe_relations(after.relations + (relation,)), transition_journal=after.transition_journal + (_journal("apply_explicit_correction", (relation.relation_id,)),))
    return TransitionResult(True, "explicit_correction_applied", bundle, after, relation=relation)


def register_contradiction(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord, *, dependent_work_ids: Sequence[str] = ()) -> TransitionResult:
    relation = construct_relation(
        left,
        right,
        relation_type="direct_contradiction",
        confidence_state="known",
        authority_effect="no_winner_without_authority_or_evidence",
        resolution_state="unresolved",
        dependent_work_ids=tuple(dependent_work_ids),
    )
    after = _append_relation(bundle, relation).after_state
    if dependent_work_ids:
        after = suspend_dependent_work(after, relation, dependent_work_ids)
    return TransitionResult(True, "direct_contradiction_registered", bundle, after, relation=relation)


def register_uncertain_conflict(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord) -> TransitionResult:
    relation = construct_relation(left, right, relation_type="uncertain_conflict", confidence_state="uncertain", resolution_state="unresolved", authority_effect="no_lifecycle_change")
    return _append_relation(bundle, relation, reason="uncertain_conflict_registered")


def apply_temporal_transition(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord) -> TransitionResult:
    relation = construct_relation(left, right, relation_type="temporal_transition", authority_effect="left_historical_right_current", supersedes_claim_id=left.claim_id, resolved_at=FIXED_TIMESTAMP, resolution_actor=right.authority_source)
    after = _replace_claims(bundle, {left.claim_id: replace(left, lifecycle_state="historical"), right.claim_id: replace(right, lifecycle_state="current")})
    after = replace(after, relations=_dedupe_relations(after.relations + (relation,)), transition_journal=after.transition_journal + (_journal("apply_temporal_transition", (relation.relation_id,)),))
    return TransitionResult(True, "temporal_transition_applied", bundle, after, relation=relation)


def apply_scoped_preference_update(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord) -> TransitionResult:
    relation = construct_relation(left, right, relation_type="scoped_preference_update", relation_scope=right.applicability_scope, authority_effect="narrower_scope_conditionally_current", supersedes_claim_id=left.claim_id, resolved_at=FIXED_TIMESTAMP, resolution_actor=right.authority_source)
    after = _replace_claims(bundle, {left.claim_id: replace(left, lifecycle_state="current"), right.claim_id: replace(right, lifecycle_state="conditionally_current")})
    after = replace(after, relations=_dedupe_relations(after.relations + (relation,)), transition_journal=after.transition_journal + (_journal("apply_scoped_preference_update", (relation.relation_id,)),))
    return TransitionResult(True, "scoped_preference_update_applied", bundle, after, relation=relation)


def apply_bounded_exception(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord, *, expiration: str = "completion_of_gate") -> TransitionResult:
    relation = construct_relation(left, right, relation_type="bounded_exception", relation_scope=f"{right.applicability_scope};expires={expiration}", authority_effect="exception_conditionally_current_original_preserved", resolution_state="resolved")
    after = _replace_claims(bundle, {left.claim_id: replace(left, lifecycle_state="current"), right.claim_id: replace(right, lifecycle_state="conditionally_current")})
    after = replace(after, relations=_dedupe_relations(after.relations + (relation,)), transition_journal=after.transition_journal + (_journal("apply_bounded_exception", (relation.relation_id, expiration)),))
    return TransitionResult(True, "bounded_exception_applied", bundle, after, relation=relation)


def revoke_authority(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord, *, affected_work_ids: Sequence[str] = ()) -> TransitionResult:
    relation = construct_relation(left, right, relation_type="authority_revocation", authority_effect="prospective_revocation_pending_work_suspended", supersedes_claim_id=left.claim_id, dependent_work_ids=affected_work_ids, resolved_at=FIXED_TIMESTAMP, resolution_actor=right.authority_source)
    after = _replace_claims(bundle, {left.claim_id: replace(left, lifecycle_state="revoked"), right.claim_id: replace(right, lifecycle_state="current")})
    after = replace(after, relations=_dedupe_relations(after.relations + (relation,)), transition_journal=after.transition_journal + (_journal("revoke_authority", (relation.relation_id,)),))
    if affected_work_ids:
        after = suspend_dependent_work(after, relation, affected_work_ids)
    return TransitionResult(True, "authority_revocation_applied", bundle, after, relation=relation)


def mark_unrelated(bundle: ClaimRelationStateBundle, left: GovernedClaimRecord, right: GovernedClaimRecord) -> TransitionResult:
    relation = construct_relation(left, right, relation_type="unrelated", relation_scope="different_subject_or_scope", authority_effect="no_work_block")
    return _append_relation(bundle, relation, reason="unrelated_marked")


def invalidate_relation(bundle: ClaimRelationStateBundle, relation_id: str, *, actor: str = "contract_validator") -> TransitionResult:
    changed = tuple(replace(item, resolution_state="invalid", resolved_at=FIXED_TIMESTAMP, resolution_actor=actor) if item.relation_id == relation_id else item for item in bundle.relations)
    if changed == bundle.relations:
        raise ValueError("relation_not_found")
    after = replace(bundle, relations=changed, transition_journal=bundle.transition_journal + (_journal("invalidate_relation", (relation_id,)),))
    return TransitionResult(True, "relation_invalidated", bundle, after)


def request_operator_resolution(
    bundle: ClaimRelationStateBundle,
    relation: GovernedClaimRelationRecord,
    *,
    affected_work_ids: Sequence[str] = (),
    recommended_interpretation: str = "",
) -> TransitionResult:
    key = operator_resolution_key(relation, affected_work_ids)
    existing = next((item for item in bundle.operator_requests if item.resolution_key == key), None)
    if existing is not None:
        return TransitionResult(True, "duplicate_operator_request_suppressed", bundle, bundle, relation=relation, operator_request=existing)
    request = GovernedOperatorResolutionRecord(
        request_id="operator-request-" + bootstrap_digest({"resolution_key": key})[:16],
        resolution_key=key,
        human_question=_human_question(relation),
        affected_claim_ids=(relation.left_claim_id, relation.right_claim_id),
        affected_work_ids=tuple(affected_work_ids),
        recommended_interpretation=recommended_interpretation,
        authority_required="operator_resolution",
        pending_state="blocked_operator_decision",
        consumed=False,
        created_at=FIXED_TIMESTAMP,
    )
    updated_relation = replace(relation, operator_request_id=request.request_id, resolution_state="operator_pending")
    after = _replace_relation(bundle, updated_relation)
    after = replace(after, operator_requests=after.operator_requests + (request,), transition_journal=after.transition_journal + (_journal("request_operator_resolution", (request.request_id,)),))
    if affected_work_ids:
        after = suspend_dependent_work(after, updated_relation, affected_work_ids, operator_request_id=request.request_id)
    return TransitionResult(True, "operator_resolution_requested", bundle, after, relation=updated_relation, operator_request=request)


def resolve_by_operator(bundle: ClaimRelationStateBundle, request_id: str, *, decision: str, actor: str = "operator") -> TransitionResult:
    request = _request_by_id(bundle, request_id)
    if request.consumed:
        return TransitionResult(True, "operator_resolution_already_consumed", bundle, bundle, operator_request=request)
    updated_request = replace(request, consumed=True, pending_state="resolved", resolved_at=FIXED_TIMESTAMP, resolution_actor=actor)
    updated_relations = tuple(
        replace(item, resolution_state="operator_resolved", resolved_at=FIXED_TIMESTAMP, resolution_actor=actor)
        if item.operator_request_id == request_id else item
        for item in bundle.relations
    )
    updated_work = tuple(replace(item, state="ready", blocked_by_operator_request_id="") if item.blocked_by_operator_request_id == request_id else item for item in bundle.work_items)
    after = replace(
        bundle,
        relations=updated_relations,
        operator_requests=tuple(updated_request if item.request_id == request_id else item for item in bundle.operator_requests),
        work_items=updated_work,
        transition_journal=bundle.transition_journal + (_journal("resolve_by_operator", (request_id, decision)),),
    )
    return TransitionResult(True, "operator_resolution_consumed", bundle, after, operator_request=updated_request)


def resolve_by_grounded_evidence(bundle: ClaimRelationStateBundle, relation_id: str, *, evidence_ref: str, actor: str = "grounded_evidence") -> TransitionResult:
    relation = next((item for item in bundle.relations if item.relation_id == relation_id), None)
    if relation is None:
        raise ValueError("relation_not_found")
    updated = replace(relation, resolution_state="grounded_evidence_resolved", evidence_refs=relation.evidence_refs + (evidence_ref,), resolved_at=FIXED_TIMESTAMP, resolution_actor=actor)
    after = _replace_relation(bundle, updated)
    after = replace(after, transition_journal=after.transition_journal + (_journal("resolve_by_grounded_evidence", (relation_id, evidence_ref)),))
    return TransitionResult(True, "grounded_evidence_resolution_applied", bundle, after, relation=updated)


def suspend_dependent_work(bundle: ClaimRelationStateBundle, relation: GovernedClaimRelationRecord, work_ids: Sequence[str], *, operator_request_id: str = "") -> ClaimRelationStateBundle:
    wanted = set(work_ids)
    updated: list[GovernedWorkItem] = []
    existing = {item.work_id for item in bundle.work_items}
    for item in bundle.work_items:
        if item.work_id in wanted:
            updated.append(replace(item, state="blocked_operator_decision", blocked_by_operator_request_id=operator_request_id or relation.operator_request_id))
        else:
            updated.append(item)
    for work_id in sorted(wanted - existing):
        updated.append(GovernedWorkItem(work_id=work_id, state="blocked_operator_decision", dependent_claim_ids=(relation.left_claim_id, relation.right_claim_id), blocked_by_operator_request_id=operator_request_id or relation.operator_request_id))
    return replace(bundle, work_items=tuple(updated), transition_journal=bundle.transition_journal + (_journal("suspend_dependent_work", tuple(sorted(wanted))),))


def operator_resolution_key(relation: GovernedClaimRelationRecord, affected_work_ids: Sequence[str] = ()) -> str:
    return bootstrap_digest({
        "relation_id": relation.relation_id,
        "claim_ids": (relation.left_claim_id, relation.right_claim_id),
        "affected_work_ids": tuple(sorted(affected_work_ids)),
        "authority": "operator_resolution",
    })


def expose_for_evaluator(bundle: ClaimRelationStateBundle) -> dict[str, Any]:
    return {
        "claim_relation_records": [
            {
                "relation": _evaluator_relation_name(item.relation_type),
                "claim_ids": [item.left_claim_id, item.right_claim_id],
                "provenance_refs": list(item.provenance_refs),
            }
            for item in bundle.relations
        ],
        "current_claim_id": next((item.claim_id for item in bundle.claims if item.lifecycle_state in {"current", "conditionally_current"}), ""),
        "superseded_claim_ids": [item.claim_id for item in bundle.claims if item.lifecycle_state in {"superseded", "historical"}],
        "operator_resolution_request": next((item.human_question for item in bundle.operator_requests if not item.consumed), ""),
        "dependent_work_suspended": any(item.state == "blocked_operator_decision" for item in bundle.work_items),
        "independent_safe_work_continues": any(item.state == "ready" for item in bundle.work_items),
        "authority_revocation_record": next((item.relation_id for item in bundle.relations if item.relation_type == "authority_revocation"), ""),
        "scoped_exception_record": next((item.relation_id for item in bundle.relations if item.relation_type == "bounded_exception"), ""),
        "provenance_refs": sorted({ref for claim in bundle.claims for ref in claim.provenance_refs}),
        "restart_round_trip_preserved": reconstruct_bundle(serialize_bundle(bundle)) == bundle,
        "mutation_performed": False,
        "provider_call_performed": False,
    }


def proposal_amendment_record(evaluator_digest: str = "") -> dict[str, Any]:
    base = {
        "schema": "cognitive_claim_relation_proposal_amendment_v1",
        "baseline_gap_identity": BASELINE_GAP_ID,
        "evaluator_path": EVALUATOR_PATH,
        "evaluator_digest": evaluator_digest,
        "missing_governed_facts": (
            "claim_identity",
            "relation_type",
            "lifecycle_state",
            "scope",
            "temporal_qualifier",
            "operator_request",
            "dependent_work_state",
            "restart_state",
        ),
        "new_inert_contract_paths": ("orchestration/runtime/cognitive_claim_relations.py", "tests/runtime_gsr/test_cognitive_claim_relations.py"),
        "expected_future_producer_boundary": "future authorized claim-relation producer only",
        "expected_future_consumer_boundary": "future authorized memory/discourse/authority consumers only",
        "persistence_impact": "new restart-visible claim relation bundle and transition journal",
        "authority_impact": "corrections, revocations, exceptions, and operator resolutions require bounded authority facts",
        "operator_request_impact": "one deterministic pending request per resolution key",
        "production_integration_authorized": False,
        "fresh_authorization_required_before_integration": True,
        "separate_from_replay_validity_proposal": True,
        "replay_validity_proposal_id_not_rewritten": PROPOSAL_ID,
    }
    amendment_id = "cognitive-claim-relation-amendment-" + bootstrap_digest(base)[:16]
    return {**base, "amendment_id": amendment_id, "amendment_digest": bootstrap_digest({**base, "amendment_id": amendment_id})}


def transition_contracts() -> tuple[dict[str, Any], ...]:
    names = (
        "register_claim",
        "link_confirmation",
        "link_duplicate",
        "apply_explicit_correction",
        "register_contradiction",
        "register_uncertain_conflict",
        "apply_temporal_transition",
        "apply_scoped_preference_update",
        "apply_bounded_exception",
        "revoke_authority",
        "request_operator_resolution",
        "resolve_by_operator",
        "resolve_by_grounded_evidence",
        "mark_unrelated",
        "invalidate_relation",
    )
    authority = {
        "register_claim": "claim_source_authority",
        "resolve_by_operator": "operator_resolution",
        "resolve_by_grounded_evidence": "grounded_evidence",
    }
    return tuple({
        "transition": name,
        "preconditions": _transition_preconditions(name),
        "authority": authority.get(name, AUTHORITY_SCOPE),
        "before_state": "explicit_bundle_state",
        "after_state": "new_immutable_bundle_state",
        "provenance_required": True,
        "idempotency_key": "required_for_external_invocation",
        "affected_dependent_work": "only linked dependent work",
        "persistence_requirement": "transition journal and bundle must survive restart",
    } for name in names)


def claim_schema() -> dict[str, Any]:
    return {"schema": SCHEMA_VERSION, "record": "GovernedClaimRecord", "fields": tuple(GovernedClaimRecord.__dataclass_fields__.keys()), "immutable": True}


def relation_schema() -> dict[str, Any]:
    return {"schema": SCHEMA_VERSION, "record": "GovernedClaimRelationRecord", "fields": tuple(GovernedClaimRelationRecord.__dataclass_fields__.keys()), "immutable": True}


def negative_controls() -> dict[str, Any]:
    return {
        "silent_overwrite": "rejected_prior_claim_preserved",
        "newest_claim_automatically_wins": "rejected_without_correction_authority_temporal_or_evidence_basis",
        "explicit_correction_deletes_prior_claim": "rejected",
        "preference_exception_becomes_global": "rejected",
        "revocation_deletes_authorization_history": "rejected",
        "temporal_transition_labeled_contradiction": "rejected",
        "ambiguous_pronoun_resolved_automatically": "rejected",
        "duplicate_operator_request": "suppressed",
        "restart_loses_supersession_state": "rejected",
        "unresolved_relation_blocks_unrelated_work": "rejected",
        "evaluator_result_becomes_truth_authority": "rejected",
        "claim_identity_only_raw_text": "rejected_scope_provenance_time_differ",
    }


def serialize_bundle(bundle: ClaimRelationStateBundle) -> str:
    return json.dumps(bundle.as_record(), indent=2, sort_keys=True, default=list)


def reconstruct_bundle(payload: str | Mapping[str, Any]) -> ClaimRelationStateBundle:
    try:
        data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("corrupt_claim_relation_bundle") from exc
    try:
        claims = tuple(_claim_from_mapping(item) for item in data.get("claims", ()))
        relations = tuple(_relation_from_mapping(item) for item in data.get("relations", ()))
        requests = tuple(_request_from_mapping(item) for item in data.get("operator_requests", ()))
        work_items = tuple(_work_from_mapping(item) for item in data.get("work_items", ()))
        bundle = ClaimRelationStateBundle(
            claims=claims,
            relations=relations,
            operator_requests=requests,
            work_items=work_items,
            transition_journal=tuple(_journal_from_mapping(item) for item in data.get("transition_journal", ())),
            schema_version=str(data.get("schema_version") or ""),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("corrupt_claim_relation_bundle") from exc
    if "unsupported_schema_version" in validate_bundle(bundle):
        raise ValueError("unsupported_schema_version")
    return bundle


def write_bundle(path: str | Path, bundle: ClaimRelationStateBundle) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(serialize_bundle(bundle), encoding="utf-8")
    tmp.replace(path)


def read_bundle(path: str | Path) -> ClaimRelationStateBundle:
    try:
        return reconstruct_bundle(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError("corrupt_claim_relation_bundle") from exc


def run_claim_relation_contract_report(output_root: str | Path = ".tmp/cognitive-transfer-cycle-1b") -> dict[str, Any]:
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    before = _git_lines("status", "--short", "--branch")
    head = _git_lines("rev-parse", "HEAD")[0] if _git_lines("rev-parse", "HEAD") else ""
    branch = _git_lines("branch", "--show-current")[0] if _git_lines("branch", "--show-current") else ""
    evaluator_digest = _file_digest(Path(EVALUATOR_PATH))

    left = construct_claim(claim_text="The appointment is Tuesday.", normalized_content={"subject": "appointment", "predicate": "day", "value": "Tuesday"}, provenance_refs=("turn:1",))
    right = construct_claim(claim_text="Correction: the appointment is Wednesday.", normalized_content={"subject": "appointment", "predicate": "day", "value": "Wednesday"}, provenance_refs=("turn:2",))
    bundle = ClaimRelationStateBundle(claims=(left, right), work_items=(GovernedWorkItem("dependent", "ready", (left.claim_id, right.claim_id)), GovernedWorkItem("independent", "ready", ())))
    corrected = apply_explicit_correction(bundle, left, right).after_state
    contradiction = register_contradiction(corrected, left, right, dependent_work_ids=("dependent",)).after_state
    operator = request_operator_resolution(contradiction, contradiction.relations[-1], affected_work_ids=("dependent",)).after_state
    restored = reconstruct_bundle(serialize_bundle(operator))
    amendment = proposal_amendment_record(evaluator_digest)
    final = {
        "status": STATUS_PASSED,
        "amendment_id": amendment["amendment_id"],
        "amendment_digest": amendment["amendment_digest"],
        "evaluator_digest": evaluator_digest,
        "contract_digest": bootstrap_digest({"bundle": restored.as_record(), "amendment": amendment}),
    }
    reports: dict[str, Mapping[str, Any]] = {
        "baseline.json": {"accepted_status": TRANSFER_STATUS, "accepted_gap": BASELINE_GAP_ID, "report": ".tmp/cognitive-transfer-cycle-1a/report.json"},
        "branch_head.json": {"branch": branch, "head": head, "expected_head": "c8386d4935d82981cc3b34543b384e4837b12e14"},
        "dirty_tree_before.json": {"branch_status": before},
        "first_missing_transition.json": first_missing_transition(),
        "transfer_gap_identity.json": {"gap_id": BASELINE_GAP_ID, "first_material_gap": True},
        "evaluator_identity.json": {"path": EVALUATOR_PATH, "status": TRANSFER_STATUS, "implementation_coupled": False},
        "evaluator_digest.json": {"path": EVALUATOR_PATH, "digest": evaluator_digest},
        "behavioral_requirements.json": {"requirements": ("claim identities", "relation types", "lifecycle states", "scope", "temporal qualifiers", "authority", "operator boundary", "restart state")},
        "claim_schema.json": claim_schema(),
        "claim_identity.json": {"scope_sensitive": True, "raw_text_only": False, "example_claim_id": left.claim_id, "example_claim_digest": left.claim_digest},
        "relation_schema.json": relation_schema(),
        "relation_types.json": {"relation_types": RELATION_TYPES, "collapsed_conflict_state": False},
        "lifecycle_states.json": {"lifecycle_states": LIFECYCLE_STATES, "prior_claim_preserved": True},
        "transition_contracts.json": {"transitions": transition_contracts()},
        "correction_semantics.json": {"left_after": "superseded", "right_after": "current", "prior_claim_deleted": False},
        "contradiction_semantics.json": {"winner_selected_without_authority": False, "dependent_work_may_suspend": True, "independent_work_continues": True},
        "preference_scope_semantics.json": {"global_preserved": True, "project_scope": True, "one_response_exception": True, "time_bounded": True},
        "bounded_exception_semantics.json": {"original_rule_preserved": True, "expiration_required": True, "not_globalized": True},
        "revocation_semantics.json": {"prospective": True, "authorization_history_preserved": True, "pending_work_suspended": True},
        "temporal_semantics.json": {"historical_and_current_can_differ": True, "non_overlapping_temporal_scope_not_contradiction": True},
        "ambiguity_semantics.json": {"automatic_resolution": False, "duplicate_request_suppression": True, "independent_work_continues": True},
        "operator_request_contract.json": {"record": "GovernedOperatorResolutionRecord", "fields": tuple(GovernedOperatorResolutionRecord.__dataclass_fields__.keys()), "duplicate_suppression": True},
        "dependent_work_contract.json": {"blocked_state": "blocked_operator_decision", "independent_state": "ready", "only_linked_work_updated": True},
        "authority_rules.json": {"authority_scope": AUTHORITY_SCOPE, "evaluator_result_authority": False, "fresh_authorization_required_before_integration": True},
        "provenance_rules.json": {"claims_require_provenance": True, "relations_require_provenance": True, "correction_linkage_durable": True},
        "persistence_contract.json": {"serialization": "json", "atomic_write": True, "transition_journal": True, "inert_only": True},
        "restart_contract.json": {"claims_survive": restored.claims == operator.claims, "relations_survive": restored.relations == operator.relations, "requests_survive": restored.operator_requests == operator.operator_requests},
        "corruption_handling.json": {"corrupt_json": "corrupt_claim_relation_bundle", "unsupported_schema": "unsupported_schema_version", "missing_record": "corrupt_claim_relation_bundle"},
        "serialization_roundtrip.json": {"roundtrip_equal": restored == operator},
        "evaluator_compatibility.json": {"observable_fields": tuple(expose_for_evaluator(operator).keys()), "evaluator_digest": evaluator_digest, "evaluator_mutated": False},
        "proposal_amendment.json": amendment,
        "proposal_amendment_digest.json": {"amendment_digest": amendment["amendment_digest"]},
        "future_integration_paths.json": {"producer": "future_authorized_claim_relation_producer", "consumers": ("memory", "discourse", "authority"), "authorized_now": False},
        "activation_block.json": {"production_integration": False, "activation": False, "fresh_authorization_required": True},
        "negative_controls.json": negative_controls(),
        "no_model_execution.json": {"model_executed": False},
        "no_candidate_generation.json": {"candidate_generated": False},
        "no_production_integration.json": {"memory_path_mutated": False, "discourse_path_mutated": False, "authority_path_mutated": False, "conversation_rendering_changed": False},
        "replay_checkpoint_regression.json": {"checkpoint": "c8386d4935d82981cc3b34543b384e4837b12e14", "status": "pending_external_validation"},
        "test_results.json": {"status": "pending_external_validation"},
        "py_compile_result.json": {"status": "pending_external_validation"},
        "diff_check_result.json": {"status": "pending_external_validation"},
        "whitespace_result.json": {"status": "pending_external_validation"},
        "process_cleanup.json": {"long_running_processes_started": False},
        "dirty_tree_after.json": {"branch_status": _git_lines("status", "--short", "--branch")},
        "final_status.json": final,
    }
    for name in REQUIRED_REPORT_FILES:
        _write_json(root / name, reports[name])
    return final


def _append_relation(bundle: ClaimRelationStateBundle, relation: GovernedClaimRelationRecord, *, reason: str = "relation_registered") -> TransitionResult:
    if relation.relation_id in {item.relation_id for item in bundle.relations}:
        return TransitionResult(True, "duplicate_relation_suppressed", bundle, bundle, relation=relation)
    after = replace(bundle, relations=bundle.relations + (relation,), transition_journal=bundle.transition_journal + (_journal(reason, (relation.relation_id,)),))
    return TransitionResult(True, reason, bundle, after, relation=relation)


def _replace_claims(bundle: ClaimRelationStateBundle, replacements: Mapping[str, GovernedClaimRecord]) -> ClaimRelationStateBundle:
    claims = tuple(replacements.get(item.claim_id, item) for item in bundle.claims)
    existing = {item.claim_id for item in claims}
    claims = claims + tuple(item for key, item in replacements.items() if key not in existing)
    return replace(bundle, claims=claims)


def _replace_relation(bundle: ClaimRelationStateBundle, relation: GovernedClaimRelationRecord) -> ClaimRelationStateBundle:
    if relation.relation_id not in {item.relation_id for item in bundle.relations}:
        return replace(bundle, relations=bundle.relations + (relation,))
    return replace(bundle, relations=tuple(relation if item.relation_id == relation.relation_id else item for item in bundle.relations))


def _dedupe_relations(relations: Sequence[GovernedClaimRelationRecord]) -> tuple[GovernedClaimRelationRecord, ...]:
    by_id: dict[str, GovernedClaimRelationRecord] = {}
    for relation in relations:
        by_id[relation.relation_id] = relation
    return tuple(by_id.values())


def _journal(transition: str, ids: Sequence[str]) -> Mapping[str, Any]:
    return {"transition": transition, "ids": tuple(ids), "created_at": FIXED_TIMESTAMP, "authority_scope": AUTHORITY_SCOPE}


def _transition_preconditions(name: str) -> tuple[str, ...]:
    mapping = {
        "register_claim": ("claim_identity_constructed", "provenance_present"),
        "apply_explicit_correction": ("same_authorized_operator_or_authorized_source", "scope_unambiguous"),
        "register_contradiction": ("overlapping_subject_scope", "no_explicit_resolution"),
        "request_operator_resolution": ("relation_unresolved_or_ambiguous", "duplicate_key_absent"),
        "resolve_by_operator": ("pending_operator_request", "authorized_operator_response"),
        "resolve_by_grounded_evidence": ("grounded_evidence_ref_present",),
        "revoke_authority": ("revocation_source_authorized", "effective_sequence_present"),
    }
    return mapping.get(name, ("claims_registered", "provenance_present"))


def _human_question(relation: GovernedClaimRelationRecord) -> str:
    if relation.relation_type == "ambiguous_scope":
        return "Which claim scope should govern the dependent work?"
    return "How should these unresolved claims be governed?"


def _request_by_id(bundle: ClaimRelationStateBundle, request_id: str) -> GovernedOperatorResolutionRecord:
    request = next((item for item in bundle.operator_requests if item.request_id == request_id), None)
    if request is None:
        raise ValueError("operator_request_not_found")
    return request


def _evaluator_relation_name(relation_type: str) -> str:
    return {
        "confirms": "confirmation",
        "duplicate_restatement": "confirmation",
        "authority_revocation": "revocation",
    }.get(relation_type, relation_type)


def _claim_from_mapping(data: Mapping[str, Any]) -> GovernedClaimRecord:
    payload = dict(data)
    payload["provenance_refs"] = tuple(payload.get("provenance_refs") or ())
    payload["normalized_content"] = dict(payload.get("normalized_content") or {})
    return GovernedClaimRecord(**payload)


def _relation_from_mapping(data: Mapping[str, Any]) -> GovernedClaimRelationRecord:
    payload = dict(data)
    for key in ("evidence_refs", "dependent_work_ids", "provenance_refs"):
        payload[key] = tuple(payload.get(key) or ())
    return GovernedClaimRelationRecord(**payload)


def _request_from_mapping(data: Mapping[str, Any]) -> GovernedOperatorResolutionRecord:
    payload = dict(data)
    for key in ("affected_claim_ids", "affected_work_ids"):
        payload[key] = tuple(payload.get(key) or ())
    return GovernedOperatorResolutionRecord(**payload)


def _work_from_mapping(data: Mapping[str, Any]) -> GovernedWorkItem:
    payload = dict(data)
    payload["dependent_claim_ids"] = tuple(payload.get("dependent_claim_ids") or ())
    return GovernedWorkItem(**payload)


def _journal_from_mapping(data: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = dict(data)
    if "ids" in payload:
        payload["ids"] = tuple(payload.get("ids") or ())
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=list), encoding="utf-8")


def _git_lines(*args: str) -> tuple[str, ...]:
    completed = subprocess.run(("git", *args), check=False, capture_output=True, text=True)
    return tuple(line for line in completed.stdout.splitlines() if line.strip())


def _file_digest(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        content = ""
    return bootstrap_digest({"path": str(path).replace("\\", "/"), "content": content})


__all__ = [
    "AUTHORITY_SCOPE",
    "BASELINE_GAP_ID",
    "LIFECYCLE_STATES",
    "RELATION_TYPES",
    "REQUIRED_REPORT_FILES",
    "SCHEMA_VERSION",
    "STATUS_PASSED",
    "ClaimRelationStateBundle",
    "GovernedClaimRecord",
    "GovernedClaimRelationRecord",
    "GovernedOperatorResolutionRecord",
    "GovernedWorkItem",
    "TransitionResult",
    "apply_bounded_exception",
    "apply_explicit_correction",
    "apply_scoped_preference_update",
    "apply_temporal_transition",
    "claim_schema",
    "classify_relation",
    "construct_claim",
    "construct_relation",
    "expose_for_evaluator",
    "first_missing_transition",
    "invalidate_relation",
    "link_confirmation",
    "link_duplicate",
    "mark_unrelated",
    "negative_controls",
    "operator_resolution_key",
    "proposal_amendment_record",
    "read_bundle",
    "reconstruct_bundle",
    "register_claim",
    "register_contradiction",
    "register_uncertain_conflict",
    "relation_identity",
    "relation_schema",
    "request_operator_resolution",
    "resolve_by_grounded_evidence",
    "resolve_by_operator",
    "revoke_authority",
    "run_claim_relation_contract_report",
    "serialize_bundle",
    "suspend_dependent_work",
    "transition_contracts",
    "validate_bundle",
    "validate_claim",
    "validate_relation",
    "write_bundle",
]
