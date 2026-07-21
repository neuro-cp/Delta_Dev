"""Pure, bounded resource and authority policy for developmental agenda goals.

This module observes caller-owned resource references and compiles one governed
next action.  It owns no resource content, request lifecycle, evaluator, agenda,
or persistence mechanism.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


MAX_POLICY_CANDIDATES = 11
REQUEST_ACTIONS = frozenset({
    "request_local_model_resource", "request_operator_teaching_resource",
    "request_operator_sealed_evaluator", "request_external_research_authority",
    "request_execution_authority",
})
FULFILLMENT_TYPES = frozenset({
    "operator_teaching_resource_fulfillment",
    "operator_sealed_evaluator_fulfillment",
    "local_model_request_approval",
    "local_model_result_fulfillment",
    "external_research_fulfillment",
    "execution_authority_fulfillment",
    "partial_fulfillment",
    "fulfillment_rejected",
    "fulfillment_deferred",
    "fulfillment_invalid",
    "fulfillment_unavailable",
})


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _words(*values: Any) -> str:
    return " ".join(str(value or "").replace("_", " ").lower() for value in values)


def _same_scope(resource: Mapping[str, Any], requirement: DevelopmentalResourceAuthorityRequirement | Mapping[str, Any]) -> bool:
    topic = str(resource.get("topic") or "")
    required_topic = str(requirement.topic if isinstance(requirement, DevelopmentalResourceAuthorityRequirement) else requirement.get("topic") or "")
    return bool(topic and required_topic and topic == required_topic)


@dataclass(frozen=True)
class DevelopmentalResourceAuthorityRequirement:
    requirement_id: str
    agenda_id: str
    mission_id: str
    goal_id: str
    proposal_id: str
    domain: str
    topic: str
    target_capability: str
    target_behavior: str
    information_need_ids: tuple[str, ...]
    current_resource_ids: tuple[str, ...]
    retained_resource_state: str
    provisional_resource_state: str
    local_model_result_state: str
    evaluator_plan_id: str
    evaluator_state: str
    evaluator_independence_state: str
    teaching_source_constraints: tuple[str, ...]
    sealed_source_constraints: tuple[str, ...]
    provenance_requirements: tuple[str, ...]
    authority_requirements: tuple[str, ...]
    execution_requirements: tuple[str, ...]
    external_source_requirements: tuple[str, ...]
    resource_budget: int
    request_budget: int
    authority_request_budget: int
    risk_budget: float
    uncertainty: str
    blockers: tuple[str, ...]
    semantic_identity: str
    requirement_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalResourceObservation:
    resource_id: str
    source_type: str
    topic: str
    mission_binding: str
    provenance: tuple[str, ...]
    validation_state: str
    uncertainty: str
    evaluator_compatible: bool
    teaching_compatible: bool
    available: bool
    digest: str
    rejection_reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalResourcePolicyCandidate:
    policy_candidate_id: str
    requirement_id: str
    action_type: str
    target_resource_id: str
    target_request_id: str
    expected_outcome: str
    permission_state: str
    availability: bool
    provenance_state: str
    independence_state: str
    cost: float
    risk: float
    request_count: int
    expected_information_gain: float
    evaluator_compatible: bool
    agenda_impact: str
    budget_fit: bool
    blockers: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    rank: float
    candidate_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalResourceAuthorityDecision:
    decision_id: str
    requirement_id: str
    selected_policy_candidate_id: str
    action_type: str
    target_resource_id: str
    target_request_id: str
    target_authority_request_id: str
    rationale: str
    rejected_candidate_ids: tuple[str, ...]
    permission_state: str
    expected_state_transition: str
    agenda_effect: str
    budget_effect: Mapping[str, int]
    stopping_condition: str
    retry_condition: str
    created_at: str
    decision_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalResourceAuthorityFulfillment:
    """Validated, typed evidence that may resolve one resource-policy blocker.

    The record keeps ownership with the caller: it records source identity and
    validation results, but does not become a second resource store or execute
    model, web, PCM, or tracked-source work.
    """

    fulfillment_id: str
    agenda_id: str
    mission_id: str
    goal_id: str
    proposal_id: str
    requirement_id: str
    policy_decision_id: str
    authority_request_id: str
    operator_interaction_id: str
    fulfillment_type: str
    source_identity: str
    source_type: str
    source_reference: str
    source_digest: str
    supplied_by: str
    scope: str
    topic: str
    target_capability: str
    intended_role: str
    provenance: tuple[str, ...]
    provenance_state: str
    integrity_state: str
    scope_compatibility: str
    evaluator_independence_state: str
    teaching_compatibility: str
    evaluator_compatibility: str
    authority_state: str
    validation_errors: tuple[str, ...]
    uncertainty: str
    partial_sections: tuple[str, ...]
    accepted_components: tuple[str, ...]
    rejected_components: tuple[str, ...]
    blocker_resolution_state: str
    semantic_identity: str
    fulfillment_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _case_kinds(payload: Mapping[str, Any]) -> set[str]:
    return {
        str(dict(item).get("case_kind") or dict(item).get("kind") or "")
        for item in (payload.get("sealed_evaluation_cases") or ())
        if isinstance(item, Mapping)
    }


def compile_developmental_resource_authority_fulfillment(
    requirement: DevelopmentalResourceAuthorityRequirement | Mapping[str, Any],
    decision: DevelopmentalResourceAuthorityDecision | Mapping[str, Any],
    *,
    authority_request_id: str,
    operator_interaction_id: str,
    supplied: Mapping[str, Any] | None,
    supplied_by: str = "operator",
) -> DevelopmentalResourceAuthorityFulfillment:
    """Validate one supplied fulfillment against the exact pending policy action."""

    required = requirement.as_dict() if isinstance(requirement, DevelopmentalResourceAuthorityRequirement) else dict(requirement or {})
    selected = decision.as_dict() if isinstance(decision, DevelopmentalResourceAuthorityDecision) else dict(decision or {})
    material = dict(supplied or {})
    action = str(selected.get("action_type") or "")
    fulfillment_type = str(material.get("fulfillment_type") or "")
    source_identity = str(material.get("source_identity") or material.get("resource_id") or material.get("result_id") or "")
    source_reference = str(material.get("source_reference") or source_identity)
    topic = str(material.get("topic") or "")
    target = str(material.get("target_capability") or "")
    provenance = tuple(str(item) for item in (material.get("provenance") or material.get("resource_provenance") or ()) if item)
    errors: list[str] = []
    accepted: list[str] = []
    rejected: list[str] = []
    partial: list[str] = []
    if fulfillment_type not in FULFILLMENT_TYPES:
        errors.append("unknown_fulfillment_type")
    expected_types = {
        "request_operator_teaching_resource": {"operator_teaching_resource_fulfillment", "partial_fulfillment"},
        "request_operator_sealed_evaluator": {"operator_sealed_evaluator_fulfillment", "partial_fulfillment"},
        "request_local_model_resource": {"local_model_request_approval", "local_model_result_fulfillment", "fulfillment_unavailable"},
        "request_external_research_authority": {"external_research_fulfillment", "partial_fulfillment", "fulfillment_unavailable"},
        "request_execution_authority": {"execution_authority_fulfillment"},
    }
    if action in expected_types and fulfillment_type not in expected_types[action]:
        errors.append("fulfillment_type_does_not_match_selected_policy_action")
    if not source_identity:
        errors.append("missing_source_identity")
    if not source_reference:
        errors.append("missing_source_reference")
    if not provenance:
        errors.append("provenance_missing")
    if topic != str(required.get("topic") or ""):
        errors.append("scope_mismatch")
    if target != str(required.get("target_capability") or ""):
        errors.append("target_capability_mismatch")
    if fulfillment_type == "operator_teaching_resource_fulfillment":
        resources = tuple(item for item in (material.get("study_resources") or ()) if isinstance(item, Mapping))
        if not resources:
            errors.append("teaching_content_unavailable")
        if material.get("sealed_evaluation_cases") or material.get("independent_evaluator"):
            errors.append("evaluator_leakage_detected")
        else:
            accepted.append("teaching_resource")
    elif fulfillment_type == "operator_sealed_evaluator_fulfillment":
        cases = tuple(item for item in (material.get("sealed_evaluation_cases") or ()) if isinstance(item, Mapping))
        kinds = _case_kinds(material)
        required_kinds = {"baseline", "control", "held_out", "adversarial", "transfer"}
        if material.get("study_resources"):
            errors.append("teaching_source_conflict")
        if not dict(material.get("independent_evaluator") or {}):
            errors.append("missing_evaluator_authority")
        if bool(material.get("candidate_mutable")):
            errors.append("mutable_by_candidate")
        if not cases:
            errors.append("sealed_cases_unavailable")
        missing_kinds = required_kinds - kinds
        if missing_kinds:
            partial.extend(sorted(missing_kinds))
            errors.append("insufficient_case_coverage")
        if not errors:
            accepted.extend(("sealed_evaluator", "sealed_cases"))
    elif fulfillment_type == "local_model_request_approval":
        if str(material.get("lifecycle_state") or "") not in {"approved", "executing"}:
            errors.append("local_model_request_not_approved")
        else:
            accepted.append("local_model_request")
    elif fulfillment_type == "local_model_result_fulfillment":
        if str(material.get("lifecycle_state") or "") != "completed" or not material.get("response_digest"):
            errors.append("local_model_result_not_completed")
        else:
            accepted.append("advisory_local_model_result")
    elif fulfillment_type == "external_research_fulfillment":
        sources = tuple(item for item in (material.get("accepted_sources") or ()) if isinstance(item, Mapping))
        resource = dict(material.get("provisional_resource") or {})
        if material.get("sealed_evaluation_cases") or material.get("independent_evaluator"):
            errors.append("evaluator_leakage_detected")
        if not sources or not resource or not resource.get("resource_bundle_id"):
            errors.append("external_research_evidence_insufficient")
        elif any(not item.get("source_record_id") or not item.get("content_digest") for item in sources):
            errors.append("external_source_provenance_incomplete")
        else:
            accepted.extend(("external_research_teaching_evidence", "provisional_external_resource"))
    elif fulfillment_type == "execution_authority_fulfillment":
        scope = _words(material.get("scope"))
        if not scope or "tracked" in scope or "deploy" in scope or "git" in scope:
            errors.append("execution_scope_not_disposable")
        else:
            accepted.append("disposable_execution_authority")
    elif fulfillment_type == "partial_fulfillment":
        partial.extend(str(item) for item in (material.get("partial_sections") or ()) if item)
        if not partial:
            errors.append("partial_fulfillment_missing_sections")
        else:
            accepted.append("partial_fulfillment")
            rejected.extend(partial)
    elif fulfillment_type in {"fulfillment_rejected", "fulfillment_deferred", "fulfillment_unavailable"}:
        rejected.append(fulfillment_type)
    elif fulfillment_type == "fulfillment_invalid":
        errors.append("operator_marked_material_invalid")
    source_digest = str(material.get("source_digest") or _digest({"identity": source_identity, "reference": source_reference, "payload": material}))
    semantic = _digest({
        "requirement": required.get("requirement_id"), "decision": selected.get("decision_id"),
        "authority": authority_request_id, "type": fulfillment_type, "source": source_identity,
        "source_digest": source_digest, "topic": topic, "target": target,
    })
    terminal = fulfillment_type in {"fulfillment_rejected", "fulfillment_deferred", "fulfillment_unavailable"}
    valid = not errors and not terminal and bool(accepted)
    blocker_state = "resolved" if valid and not partial else "partially_resolved" if valid else "unresolved"
    status = "validated" if valid and not partial else "partial" if valid else "rejected" if terminal else "invalid"
    payload = {"semantic": semantic, "status": status, "errors": tuple(sorted(errors)), "accepted": tuple(sorted(accepted)), "partial": tuple(sorted(partial))}
    return DevelopmentalResourceAuthorityFulfillment(
        fulfillment_id=stable_id("developmental-resource-fulfillment", _digest(payload)),
        agenda_id=str(required.get("agenda_id") or ""), mission_id=str(required.get("mission_id") or ""),
        goal_id=str(required.get("goal_id") or ""), proposal_id=str(required.get("proposal_id") or ""),
        requirement_id=str(required.get("requirement_id") or ""), policy_decision_id=str(selected.get("decision_id") or ""),
        authority_request_id=authority_request_id, operator_interaction_id=operator_interaction_id,
        fulfillment_type=fulfillment_type, source_identity=source_identity, source_type=str(material.get("source_type") or "operator_supplied"),
        source_reference=source_reference, source_digest=source_digest, supplied_by=supplied_by,
        scope=str(material.get("scope") or ""), topic=topic, target_capability=target,
        intended_role=str(material.get("intended_role") or ""), provenance=provenance,
        provenance_state="verified" if provenance else "missing", integrity_state="verified" if material.get("source_digest") or source_identity else "unverified",
        scope_compatibility="compatible" if "scope_mismatch" not in errors and "target_capability_mismatch" not in errors else "mismatch",
        evaluator_independence_state="independent" if fulfillment_type == "operator_sealed_evaluator_fulfillment" and not errors else "not_applicable" if fulfillment_type != "operator_sealed_evaluator_fulfillment" else "invalid",
        teaching_compatibility="compatible" if fulfillment_type == "operator_teaching_resource_fulfillment" and not errors else "not_applicable" if fulfillment_type != "operator_teaching_resource_fulfillment" else "invalid",
        evaluator_compatibility="compatible" if fulfillment_type == "operator_sealed_evaluator_fulfillment" and not errors else "not_applicable" if fulfillment_type != "operator_sealed_evaluator_fulfillment" else "invalid",
        authority_state="validated" if valid else "not_granted", validation_errors=tuple(sorted(errors)),
        uncertainty=str(material.get("uncertainty") or "resource fulfillment does not promote capability"),
        partial_sections=tuple(sorted(set(partial))), accepted_components=tuple(sorted(set(accepted))), rejected_components=tuple(sorted(set(rejected))),
        blocker_resolution_state=blocker_state, semantic_identity=semantic, fulfillment_digest=_digest(payload), status=status,
    )


def compile_developmental_resource_authority_requirement(
    *,
    agenda: Mapping[str, Any],
    proposal: Mapping[str, Any],
    candidate: Mapping[str, Any],
    mission: Mapping[str, Any] = None,
    learning_state: Mapping[str, Any] = None,
) -> DevelopmentalResourceAuthorityRequirement:
    """Describe the evidence and authority gap before any strategy is selected."""

    mission = dict(mission or {})
    state = dict(learning_state or {})
    retained = dict(state.get("retained_bundle") or {})
    provisional = dict(state.get("provisional_resource_bundle") or {})
    fulfillments = tuple(dict(item) for item in (state.get("developmental_resource_fulfillments") or ()) if isinstance(item, Mapping))
    fulfilled_teaching = any(item.get("status") == "validated" and item.get("fulfillment_type") == "operator_teaching_resource_fulfillment" for item in fulfillments)
    fulfilled_evaluator = any(item.get("status") == "validated" and item.get("fulfillment_type") == "operator_sealed_evaluator_fulfillment" for item in fulfillments)
    local_request = dict(state.get("local_model_request") or {})
    result = dict(state.get("local_model_result_reference") or {})
    strategy = dict(state.get("evaluation_strategy") or {})
    selected_plan = dict(strategy.get("selected_plan") or {})
    selected_strategy = str(selected_plan.get("selected_strategy") or "")
    selected_evaluator_available = (
        str(selected_plan.get("status") or "") == "evaluation_plan_ready"
        and bool(selected_strategy)
    )
    topic = str(proposal.get("topic") or candidate.get("topic") or mission.get("topic") or "")
    target = str(proposal.get("target_capability") or candidate.get("target_capability") or mission.get("primary_capability_target") or "")
    behavior = str(proposal.get("measurable_outcome") or candidate.get("target_behavior") or "")
    retained_state = "available_validated" if retained.get("study_resources") or fulfilled_teaching else "unavailable"
    provisional_state = "available_advisory" if provisional else "unavailable"
    model_state = str(local_request.get("lifecycle_state") or "unavailable")
    evaluator_state = "evaluation_plan_ready" if fulfilled_evaluator or selected_evaluator_available else "evaluation_unavailable"
    evaluator_independence = "independent" if fulfilled_evaluator or selected_evaluator_available else "unavailable"
    blockers: list[str] = []
    if retained_state == "unavailable" and provisional_state == "unavailable" and model_state != "completed":
        blockers.append("teaching_resource_unavailable")
    if evaluator_state == "evaluation_unavailable" or evaluator_independence != "independent":
        blockers.append("independent_evaluator_unavailable")
    if str(candidate.get("resource_state") or "") in {"unavailable", "unknown"}:
        blockers.append("resource_path_unavailable")
    if str(candidate.get("authority_state") or "") and "blocked" in str(candidate.get("authority_state")).lower():
        blockers.append("authority_unavailable")
    needs = tuple(str(item) for item in (state.get("information_need", {}).get("semantic_identity"), *proposal.get("source_evidence", ())) if item)
    resource_ids = tuple(str(item.get("resource_id") or "") for item in retained.get("study_resources") or ())
    semantic = _digest({
        "agenda": agenda.get("agenda_id"), "proposal": proposal.get("proposal_id"), "topic": topic,
        "target": target, "behavior": behavior, "needs": needs, "retained": retained.get("bundle_digest") or retained.get("resource_bundle_id"),
        "provisional": provisional.get("bundle_digest") or provisional.get("resource_bundle_id"),
        "local_request": local_request.get("request_digest"), "local_result": result.get("response_digest"),
        "evaluator": selected_plan.get("plan_id") or evaluator_state, "blockers": tuple(sorted(blockers)),
        "budgets": (agenda.get("remaining_attempt_budget"), agenda.get("remaining_proposal_budget")),
    })
    payload = {"agenda": agenda.get("agenda_id"), "proposal": proposal.get("proposal_id"), "semantic": semantic}
    return DevelopmentalResourceAuthorityRequirement(
        requirement_id=stable_id("developmental-resource-authority-requirement", semantic),
        agenda_id=str(agenda.get("agenda_id") or ""), mission_id=str(mission.get("mission_id") or ""),
        goal_id=str(candidate.get("interest_id") or proposal.get("selected_interest_id") or ""), proposal_id=str(proposal.get("proposal_id") or ""),
        domain=str(proposal.get("domain") or candidate.get("domain") or mission.get("domain") or ""), topic=topic,
        target_capability=target, target_behavior=behavior, information_need_ids=needs, current_resource_ids=resource_ids,
        retained_resource_state=retained_state, provisional_resource_state=provisional_state, local_model_result_state=model_state,
        evaluator_plan_id=str(selected_plan.get("plan_id") or ""), evaluator_state=evaluator_state, evaluator_independence_state=evaluator_independence,
        teaching_source_constraints=("teaching_evidence_cannot_certify_capability",), sealed_source_constraints=("sealed_evaluator_must_remain_separate",),
        provenance_requirements=("durable_identity", "scope_compatibility"), authority_requirements=("operator_approval_for_new_resource_or_authority",),
        execution_requirements=("execution_required", "disposable_execution_only_when_explicitly_authorized") if bool(candidate.get("execution_required")) else ("execution_not_required",), external_source_requirements=("external_research_requires_explicit_authority",) + (("external_evidence_preferred",) if str(candidate.get("resource_state") or "") in {"external_research_required", "external_evidence_required"} else ()),
        resource_budget=max(0, int(agenda.get("remaining_attempt_budget") or 0)), request_budget=1,
        authority_request_budget=max(0, 1 - sum(1 for item in state.get("resource_policy_requests") or () if item.get("status") == "pending")),
        risk_budget=0.2, uncertainty="resource routing does not establish capability", blockers=tuple(dict.fromkeys(blockers)),
        semantic_identity=semantic, requirement_digest=_digest(payload), status="requirement_compiled",
    )


def observe_developmental_resources(
    requirement: DevelopmentalResourceAuthorityRequirement,
    *,
    learning_state: Mapping[str, Any],
) -> tuple[DevelopmentalResourceObservation, ...]:
    """Normalize references only; resource content remains with its existing owner."""

    state = dict(learning_state or {})
    observed: list[DevelopmentalResourceObservation] = []
    def add(resource_id: str, source_type: str, payload: Mapping[str, Any], validation: str, uncertainty: str, evaluator: bool, teaching: bool, available: bool, reasons: Sequence[str] = ()) -> None:
        item = {**dict(payload), "topic": str(dict(payload).get("topic") or requirement.topic)}
        scope_ok = _same_scope(item, requirement)
        rejections = tuple(dict.fromkeys(tuple(str(reason) for reason in reasons) + (() if scope_ok else ("scope_mismatch",))))
        observed.append(DevelopmentalResourceObservation(
            resource_id=resource_id, source_type=source_type, topic=str(item.get("topic") or requirement.topic),
            mission_binding=str(item.get("mission_id") or ""), provenance=tuple(str(value) for value in (item.get("resource_provenance") or item.get("provenance") or ())),
            validation_state=validation, uncertainty=uncertainty, evaluator_compatible=evaluator and not rejections,
            teaching_compatible=teaching and not rejections, available=available and not rejections,
            digest=_digest({"id": resource_id, "type": source_type, "payload": item, "requirement": requirement.requirement_id}), rejection_reasons=rejections,
        ))
    retained = dict(state.get("retained_bundle") or {})
    if retained:
        has_independent_evaluator = bool(retained.get("independent_evaluator") or retained.get("sealed_evaluation_cases"))
        add(str(retained.get("resource_bundle_id") or "retained_bundle"), "validated_retained_resource", retained, "validated" if retained.get("study_resources") else "insufficient", "declared retained scope", has_independent_evaluator, bool(retained.get("study_resources")), bool(retained.get("study_resources")))
    provisional = dict(state.get("provisional_resource_bundle") or {})
    if provisional:
        add(str(provisional.get("resource_bundle_id") or "provisional_bundle"), "provisional_resource", provisional, "advisory", "model-derived provisional evidence", bool(provisional.get("independent_evaluator")), True, True)
    request = dict(state.get("local_model_request") or {})
    result = dict(state.get("local_model_result_reference") or {})
    if request:
        add(str(result.get("result_id") or request.get("request_id") or "local_model_request"), "local_model_result" if result else "local_model_request", {**request, **result, "topic": requirement.topic}, "completed" if request.get("lifecycle_state") == "completed" else str(request.get("lifecycle_state") or "pending"), "advisory model evidence", False, bool(result), bool(result), ())
    return tuple(observed)


def compile_resource_policy_candidates(
    requirement: DevelopmentalResourceAuthorityRequirement,
    observations: Sequence[DevelopmentalResourceObservation],
    *,
    has_alternative: bool,
    external_authority_granted: bool = False,
    execution_authority_granted: bool = False,
    prefer_operator_teaching: bool = False,
) -> tuple[DevelopmentalResourcePolicyCandidate, ...]:
    """Compile the bounded policy vocabulary and reject unsafe routes explicitly."""

    by_type = {item.source_type: item for item in observations}
    retained = by_type.get("validated_retained_resource")
    provisional = by_type.get("provisional_resource")
    result = by_type.get("local_model_result")
    local_request = by_type.get("local_model_request")
    teaching_rank = 0.78 if prefer_operator_teaching else 0.62
    external_preferred = "external_evidence_preferred" in requirement.external_source_requirements
    specs = (
        ("reuse_validated_retained_resource", retained, 1.0, "local_reuse_ready"),
        ("reuse_provisional_resource", provisional, 0.85, "local_reuse_ready"),
        ("reuse_existing_local_model_result", result, 0.82, "local_reuse_ready"),
        ("request_local_model_resource", None, 0.74, "awaiting_local_model_approval"),
        ("request_operator_teaching_resource", None, teaching_rank, "awaiting_operator_authority"),
        ("request_operator_sealed_evaluator", None, 0.76, "awaiting_operator_authority"),
        ("request_external_research_authority", None, 0.82 if external_preferred else 0.56, "awaiting_operator_authority"),
        ("request_execution_authority", None, 0.54, "awaiting_operator_authority"),
        ("defer_until_state_change", None, 0.18, "deferred"),
        ("return_to_agenda_alternative", None, 0.16, "agenda_alternative"),
        ("abandon_goal", None, 0.05, "abandoned"),
    )
    candidates: list[DevelopmentalResourcePolicyCandidate] = []
    for action, resource, rank, transition in specs:
        reasons: list[str] = []
        permission = "already_authorized" if action.startswith("reuse_") else "operator_authority_required"
        available = True
        compatible = True
        target = resource.resource_id if resource else ""
        if action.startswith("reuse_"):
            available = bool(resource and resource.available and resource.teaching_compatible)
            compatible = bool(resource and resource.evaluator_compatible) if action == "reuse_validated_retained_resource" else True
            if not available:
                reasons.append("matching_resource_unavailable_or_scope_mismatched")
            if action == "reuse_validated_retained_resource" and not compatible:
                available = False
                reasons.append("independent_evaluator_not_preserved")
            if action == "reuse_provisional_resource" and resource and resource.validation_state != "advisory":
                reasons.append("provisional_state_invalid")
        elif action == "request_local_model_resource":
            available = requirement.request_budget > 0 and not local_request and requirement.local_model_result_state != "completed"
            if not available:
                reasons.append("equivalent_local_model_request_or_result_exists_or_budget_exhausted")
        elif action == "request_operator_sealed_evaluator":
            available = "independent_evaluator_unavailable" in requirement.blockers and requirement.authority_request_budget > 0
            if not available:
                reasons.append("sealed_evaluator_authority_not_needed_or_budget_exhausted")
        elif action == "request_operator_teaching_resource":
            available = "teaching_resource_unavailable" in requirement.blockers and requirement.authority_request_budget > 0
            if not available:
                reasons.append("operator_teaching_resource_not_needed_or_budget_exhausted")
        elif action == "request_external_research_authority":
            available = not external_authority_granted and requirement.authority_request_budget > 0 and "teaching_resource_unavailable" in requirement.blockers
            if not available:
                reasons.append("external_research_authority_not_needed_or_already_resolved")
        elif action == "request_execution_authority":
            available = not execution_authority_granted and requirement.authority_request_budget > 0 and "execution required" in _words(requirement.execution_requirements)
            if not available:
                reasons.append("execution_authority_not_required_or_already_resolved")
        elif action == "return_to_agenda_alternative":
            available = has_alternative
            if not available:
                reasons.append("no_distinct_agenda_alternative")
        elif action == "defer_until_state_change":
            available = not any("permanent" in blocker or "corrupt" in blocker or "redundant" in blocker for blocker in requirement.blockers)
            if not available:
                reasons.append("no_credible_material_state_change")
        elif action == "abandon_goal":
            available = any(token in _words(requirement.blockers) for token in ("redundant", "unsafe", "persistently unevaluable"))
            if not available:
                reasons.append("goal_remains_valid_and_may_become_eligible")
        if requirement.resource_budget <= 0 and action not in {"defer_until_state_change", "return_to_agenda_alternative", "abandon_goal"}:
            available = False
            reasons.append("resource_budget_exhausted")
        payload = {"requirement": requirement.requirement_id, "action": action, "target": target, "reasons": tuple(sorted(reasons))}
        candidates.append(DevelopmentalResourcePolicyCandidate(
            policy_candidate_id=stable_id("developmental-resource-policy-candidate", _digest(payload)), requirement_id=requirement.requirement_id,
            action_type=action, target_resource_id=target, target_request_id="", expected_outcome=transition,
            permission_state=permission, availability=available, provenance_state="verified" if resource and resource.provenance else "required",
            independence_state="preserved" if compatible else "unavailable", cost=0.0 if action.startswith("reuse_") else 0.1,
            risk=0.02 if action.startswith("reuse_") else 0.1, request_count=0 if action.startswith("reuse_") else 1,
            expected_information_gain=rank, evaluator_compatible=compatible, agenda_impact="continue_goal" if action.startswith("reuse_") else transition,
            budget_fit=available, blockers=tuple(requirement.blockers), rejection_reasons=tuple(dict.fromkeys(reasons)), rank=rank if available else 0.0,
            candidate_digest=_digest(payload),
        ))
    return tuple(sorted(candidates[:MAX_POLICY_CANDIDATES], key=lambda item: (-item.rank, item.action_type, item.policy_candidate_id)))


def compile_resource_authority_decision(
    requirement: DevelopmentalResourceAuthorityRequirement,
    candidates: Sequence[DevelopmentalResourcePolicyCandidate],
) -> DevelopmentalResourceAuthorityDecision:
    valid = [item for item in candidates if item.availability and not item.rejection_reasons]
    selected = valid[0] if valid else None
    if selected is None:
        action = "resource_policy_unavailable"
        selected_id = ""
        transition = "agenda_blocked_or_exhausted"
        rationale = "No resource or authority action satisfies the declared scope, provenance, independence, and budget constraints."
    else:
        action = selected.action_type
        selected_id = selected.policy_candidate_id
        transition = selected.expected_outcome
        rationale = f"Selected {action} from the highest-ranked valid bounded policy candidate."
    authority_id = stable_id("developmental-resource-authority-request", requirement.semantic_identity, action) if action in REQUEST_ACTIONS else ""
    payload = {"requirement": requirement.requirement_id, "selected": selected_id, "action": action, "authority": authority_id}
    return DevelopmentalResourceAuthorityDecision(
        decision_id=stable_id("developmental-resource-authority-decision", _digest(payload)), requirement_id=requirement.requirement_id,
        selected_policy_candidate_id=selected_id, action_type=action, target_resource_id=selected.target_resource_id if selected else "",
        target_request_id=selected.target_request_id if selected else "", target_authority_request_id=authority_id, rationale=rationale,
        rejected_candidate_ids=tuple(item.policy_candidate_id for item in candidates if item is not selected),
        permission_state=selected.permission_state if selected else "unavailable", expected_state_transition=transition,
        agenda_effect=selected.agenda_impact if selected else "blocked", budget_effect={"resource_requests": int(bool(selected and selected.request_count)), "authority_requests": int(bool(authority_id))},
        stopping_condition="do_not_execute_provider_web_pcm_or_tracked_source", retry_condition="material_policy_state_change_or_explicit_operator_refresh",
        created_at=utc_now(), decision_digest=_digest(payload), status="decision_compiled",
    )


def resource_policy_state_is_valid(policy: Mapping[str, Any]) -> bool:
    requirement = dict(policy.get("requirement") or {})
    decision = dict(policy.get("decision") or {})
    candidates = tuple(dict(item) for item in (policy.get("policy_candidates") or ()) if isinstance(item, Mapping))
    if not requirement or not decision or len(candidates) > MAX_POLICY_CANDIDATES:
        return False
    if not requirement.get("requirement_id") or not requirement.get("requirement_digest"):
        return False
    if str(decision.get("requirement_id") or "") != str(requirement.get("requirement_id") or ""):
        return False
    candidate_ids = {str(item.get("policy_candidate_id") or "") for item in candidates}
    selected = str(decision.get("selected_policy_candidate_id") or "")
    if selected and selected not in candidate_ids:
        return False
    if len(candidate_ids) != len(candidates):
        return False
    return str(policy.get("status") or "") in {
        "decision_compiled", "authority_pending", "clarification_requested", "authority_granted",
        "local_model_request_pending", "awaiting_fulfillment", "fulfillment_validated", "blocker_resolved",
        "research_plan_compiled", "research_execution_claimed", "research_completed", "research_partially_completed",
        "research_failed", "research_validation_failed", "rejected", "deferred", "unavailable",
    }


def resource_fulfillment_state_is_valid(
    fulfillments: Sequence[Mapping[str, Any]],
    *,
    policy: Mapping[str, Any] | None = None,
) -> bool:
    """Fail closed if persisted fulfillment bindings or integrity summaries disagree."""

    seen: set[str] = set()
    for raw in fulfillments:
        item = dict(raw)
        semantic = str(item.get("semantic_identity") or "")
        status = str(item.get("status") or "")
        if not semantic or semantic in seen or status not in {"validated", "partial", "invalid", "rejected"}:
            return False
        if not item.get("fulfillment_id") or not item.get("requirement_id") or not item.get("policy_decision_id"):
            return False
        payload = {
            "semantic": semantic,
            "status": status,
            "errors": tuple(sorted(str(value) for value in (item.get("validation_errors") or ()))),
            "accepted": tuple(sorted(str(value) for value in (item.get("accepted_components") or ()))),
            "partial": tuple(sorted(str(value) for value in (item.get("partial_sections") or ()))),
        }
        if str(item.get("fulfillment_digest") or "") != _digest(payload):
            return False
        seen.add(semantic)
    return True


__all__ = [
    "MAX_POLICY_CANDIDATES", "REQUEST_ACTIONS", "DevelopmentalResourceAuthorityRequirement",
    "FULFILLMENT_TYPES", "DevelopmentalResourceObservation", "DevelopmentalResourcePolicyCandidate", "DevelopmentalResourceAuthorityDecision", "DevelopmentalResourceAuthorityFulfillment",
    "compile_developmental_resource_authority_requirement", "observe_developmental_resources",
    "compile_resource_policy_candidates", "compile_resource_authority_decision", "compile_developmental_resource_authority_fulfillment", "resource_policy_state_is_valid", "resource_fulfillment_state_is_valid",
]
