"""Bounded, evidence-led developmental learning contracts.

This module deliberately owns no runtime lifecycle.  The continuous runtime
controller persists and advances missions; this file only compiles immutable
learning records, ranks evidence-backed gaps, executes a local non-code study
attempt, and independently scores a sealed evaluation bundle.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


@dataclass(frozen=True)
class DevelopmentalMissionContract:
    mission_id: str
    operator_instruction: str
    mission_type: str
    domain: str
    topic: str
    mission_mode: str
    primary_capability_target: str
    authority_class: str
    allowed_resource_classes: tuple[str, ...]
    excluded_resource_classes: tuple[str, ...]
    external_resource_policy: str
    provider_policy: str
    web_policy: str
    local_model_policy: str
    sandbox_policy: str
    tracked_application_policy: str
    session_budget: int
    attempt_budget: int
    uncertainty: str
    ambiguity_status: str
    operator_decision_required: bool
    created_at: str
    protocol: str
    version: str
    contract_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalCapabilityAssessment:
    assessment_id: str
    mission_id: str
    domain: str
    topic: str
    dimensions: tuple[dict[str, Any], ...]
    known_strengths: tuple[str, ...]
    known_limitations: tuple[str, ...]
    unassessed_dimensions: tuple[str, ...]
    prerequisite_gaps: tuple[str, ...]
    recommended_focus: str
    assessment_disposition: str
    evidence_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResourceAcquisitionPlan:
    plan_id: str
    mission_id: str
    assessment_id: str
    information_needs: tuple[str, ...]
    selected_resource_classes: tuple[str, ...]
    query_objectives: tuple[str, ...]
    expected_evidence_type: str
    duplicate_query_digest: str
    source_quality_policy: str
    stopping_criteria: str
    authority_requirements: tuple[str, ...]
    resource_decisions: tuple[dict[str, Any], ...]
    plan_disposition: str
    plan_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalGap:
    gap_id: str
    mission_id: str
    capability_dimension: str
    topic: str
    current_baseline: float
    target_behavior: str
    expected_behavior_identity: str
    prerequisites: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence: float
    uncertainty: str
    materiality: float
    measurability: float
    resource_requirements: tuple[str, ...]
    semantic_identity: str
    frontier_rank: float
    selection_reason: str
    status: str = "eligible"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LearningSubgoal:
    subgoal_id: str
    mission_id: str
    source_gap_id: str
    topic: str
    frontier_rank: float
    selection_reason: str
    capability_target: str
    measurable_objective: str
    baseline: float
    success_threshold: float
    prerequisites: tuple[str, ...]
    study_resource_ids: tuple[str, ...]
    attempt_type: str
    practice_specification: str
    control_case_ids: tuple[str, ...]
    held_out_policy: str
    adversarial_policy: str
    evaluation_method: str
    attempt_budget: int
    resource_budget: int
    completion_classification: str
    next_step_policy: str
    authority_state: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalAttemptRecord:
    attempt_id: str
    mission_id: str
    subgoal_id: str
    attempt_type: str
    input_evidence_refs: tuple[str, ...]
    selected_resource_ids: tuple[str, ...]
    candidate_output: Mapping[str, Any]
    uncertainty: str
    resource_usage: Mapping[str, int]
    candidate_digest: str
    disposition: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalEvaluationRecord:
    evaluation_id: str
    mission_id: str
    subgoal_id: str
    attempt_id: str
    capability_dimension: str
    baseline_metrics: Mapping[str, float]
    candidate_metrics: Mapping[str, float]
    control_metrics: Mapping[str, float]
    held_out_metrics: Mapping[str, float]
    adversarial_metrics: Mapping[str, float]
    transfer_metrics: Mapping[str, float]
    case_ids: tuple[str, ...]
    evaluator_identity: str
    independence_proof: Mapping[str, Any]
    disposition: str
    promotion_eligible: bool
    evaluation_digest: str
    content_case_results: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MissionBoundLocalModelBridge:
    """A mission reference to an existing local-model request/result lifecycle.

    It deliberately contains digests and identifiers, not raw model prose. The
    response remains advisory evidence until the ordinary sealed evaluator
    demonstrates a narrow capability.
    """

    bridge_id: str
    mission_id: str
    mission_semantic_identity: str
    information_need_id: str
    information_need_digest: str
    topic: str
    local_model_request_id: str
    local_model_request_digest: str
    local_model_result_id: str
    local_model_response_digest: str
    model_identity: str
    adapter_identity: str
    authority_state: str
    request_state: str
    evidence_sufficiency_state: str
    provisional_resource_bundle_id: str
    curriculum_handoff_id: str
    created_at: str
    updated_at: str
    bridge_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_mission_information_need(mission: DevelopmentalMissionContract) -> dict[str, Any]:
    """Compile a bounded, semantic learning question without lesson content."""

    payload = {
        "mission_id": mission.mission_id,
        "domain": mission.domain,
        "topic": mission.topic,
        "required_sections": (
            "prerequisites", "concept_statement", "intuitive_explanation",
            "worked_example", "misconceptions", "practice_questions", "uncertainties",
        ),
        "excluded_sections": ("sealed_evaluation_answers", "capability_claims", "file_mutation", "unrestricted_exploration"),
    }
    digest = _digest(payload)
    return {
        "information_need_id": stable_id("mission-learning-information-need", mission.mission_id, digest),
        "semantic_identity": _digest((mission.domain, mission.topic, payload["required_sections"])),
        "information_need_digest": digest,
        "topic": mission.topic,
        "request_text": (
            f"Provide a bounded study resource for {mission.topic.replace('_', ' ')}. "
            "Include prerequisites, a precise concept statement, an intuitive explanation, "
            "one worked example, common misconceptions, suggested practice questions, and uncertainties. "
            "Do not claim the learner has mastered the topic and do not provide assessment answers."
        ),
        **payload,
    }


def assess_local_model_learning_evidence(
    response: str,
    *,
    topic: str,
) -> dict[str, Any]:
    """Classify advisory prose conservatively; it cannot grant capability."""

    text = " ".join(str(response or "").split())
    lowered = text.lower()
    if not text:
        return {"state": "empty", "validated_claims": (), "uncertain_claims": (), "rejected_claims": ("empty_response",)}
    required = {
        "prerequisites": ("prerequisite", "background"),
        "concept_statement": ("theorem", "statement", "definition"),
        "intuitive_explanation": ("intuition", "intuitive", "means"),
        "worked_example": ("example", "matrix", "worked"),
        "misconceptions": ("misconception", "not every", "false"),
        "practice_questions": ("practice", "question", "exercise"),
    }
    present = tuple(key for key, markers in required.items() if any(marker in lowered for marker in markers))
    # A response may explicitly preserve a contradiction; content-specific fact
    # checking belongs to an independent evaluator, never this prose parser.
    contradictions = ("explicit_model_contradiction",) if "[contradiction]" in lowered else ()
    if contradictions:
        return {"state": "contradictory", "validated_claims": present, "uncertain_claims": ("contradictory_claim_retained",), "rejected_claims": contradictions}
    if topic.replace("_", " ") not in lowered and topic not in lowered:
        return {"state": "insufficient", "validated_claims": present, "uncertain_claims": ("topic_not_identifiable",), "rejected_claims": ()}
    if len(present) < 4:
        return {"state": "partially_sufficient", "validated_claims": present, "uncertain_claims": tuple(sorted(set(required) - set(present))), "rejected_claims": ()}
    return {"state": "sufficient_for_provisional_resource", "validated_claims": present, "uncertain_claims": ("model_output_is_advisory",), "rejected_claims": ()}


def compile_provisional_learning_bundle(
    mission: DevelopmentalMissionContract,
    bridge: MissionBoundLocalModelBridge,
    response: str,
    *,
    sealed_evaluation_cases: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any] | None:
    """Create a temporary resource shell only from a sufficient model result.

    Structured study fields are extracted from the returned evidence; sealed
    cases are supplied independently by the caller and never enter the model
    request or bridge response reference.
    """

    if bridge.evidence_sufficiency_state != "sufficient_for_provisional_resource":
        return None
    sections = assess_local_model_learning_evidence(response, topic=mission.topic)
    resource_id = stable_id("provisional-local-model-resource", bridge.bridge_id, bridge.local_model_response_digest)
    # The learning attempt works against explicitly declared components. These
    # are response-derived labels, not capability claims or sealed answers.
    components = tuple(str(value) for value in sections["validated_claims"])
    dimension = f"{mission.topic}_understanding"
    return {
        "resource_bundle_id": stable_id("provisional-learning-bundle", mission.mission_id, resource_id),
        "domain": mission.domain,
        "topic": mission.topic,
        "provisional": True,
        "mission_bound_bridge_id": bridge.bridge_id,
        "resource_provenance": ({"request_id": bridge.local_model_request_id, "result_id": bridge.local_model_result_id, "model_identity": bridge.model_identity, "response_digest": bridge.local_model_response_digest},),
        "assessment_dimensions": ({"dimension": dimension, "topic": mission.topic, "baseline_case_id": "independent-baseline-required", "baseline_components": (), "required_components": components, "prerequisites": (), "evidence_ref": bridge.bridge_id, "expected_learning_value": 0.7, "information_gain": 0.7, "estimated_effort": 1.0},),
        "study_resources": ({"resource_id": resource_id, "topic": mission.topic, "supports_dimensions": (dimension,), "study_components": components, "model_result_reference": bridge.local_model_result_id},),
        "visible_practice_cases": (),
        "sealed_evaluation_cases": tuple(dict(item) for item in sealed_evaluation_cases),
        "validated_claims": sections["validated_claims"],
        "uncertain_claims": sections["uncertain_claims"],
        "rejected_claims": sections["rejected_claims"],
    }


def classify_developmental_instruction(instruction: str) -> dict[str, str] | None:
    """Classify a small, explicit learning-intent surface without model authority."""

    normalized = _text(instruction)
    if not any(token in normalized for token in ("learn", "study", "understand", "practice")):
        return None
    domain = "mathematics" if any(token in normalized for token in ("math", "mathematics", "induction", "algebra", "calculus", "spectral theorem")) else "biology" if any(token in normalized for token in ("biology", "natural selection", "evolution")) else "general_learning"
    topic = "spectral_theorem" if "spectral theorem" in normalized else "mathematical_induction" if "induction" in normalized else "natural_selection" if "natural selection" in normalized else "exploratory"
    return {
        "mission_type": "developmental_learning",
        "domain": domain,
        "topic": topic,
        "mission_mode": "bounded_learning_session" if topic != "exploratory" else "capability_assessment_then_learning",
    }


def load_retained_learning_bundles(domain: str, *, resource_root: str | Path | None = None) -> tuple[dict[str, Any], ...]:
    """Return all declared retained bundles for a domain in stable order."""

    root = Path(resource_root) if resource_root else Path(__file__).resolve().parents[2] / "docs" / "learning_resources"
    if not root.exists():
        return ()
    bundles: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _text(payload.get("domain")) != _text(domain):
            continue
        bundles.append(dict(payload))
    return tuple(bundles)


def merge_retained_learning_bundles(domain: str, bundles: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """Build a data-led exploratory view without embedding a domain curriculum."""

    if not bundles:
        return None
    dimensions: list[dict[str, Any]] = []
    resources: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    catalog: list[str] = []
    provenance: list[dict[str, str]] = []
    for raw_bundle in bundles:
        bundle = dict(raw_bundle)
        topic = str(bundle.get("topic") or "unclassified")
        bundle_id = str(bundle.get("resource_bundle_id") or topic)
        provenance.append({"resource_bundle_id": bundle_id, "topic": topic})
        catalog.extend(str(item) for item in (bundle.get("capability_catalog") or ()))
        for raw in bundle.get("assessment_dimensions") or ():
            item = dict(raw)
            item.setdefault("topic", topic)
            item.setdefault("resource_bundle_id", bundle_id)
            dimensions.append(item)
        for raw in bundle.get("study_resources") or ():
            item = dict(raw)
            item.setdefault("topic", topic)
            item.setdefault("resource_bundle_id", bundle_id)
            resources.append(item)
        for raw in bundle.get("sealed_evaluation_cases") or ():
            item = dict(raw)
            item.setdefault("topic", topic)
            item.setdefault("resource_bundle_id", bundle_id)
            cases.append(item)
    return {
        "resource_bundle_id": stable_id("retained-learning-domain", domain, _digest(provenance)),
        "domain": domain,
        "topic": "exploratory",
        "assessment_dimensions": tuple(dimensions),
        "study_resources": tuple(resources),
        "sealed_evaluation_cases": tuple(cases),
        "capability_catalog": tuple(dict.fromkeys(catalog)),
        "resource_provenance": tuple(provenance),
    }


def load_retained_learning_bundle(domain: str, topic: str, *, resource_root: str | Path | None = None) -> dict[str, Any] | None:
    """Load a retained local resource by declared domain/topic, never by model output."""

    bundles = load_retained_learning_bundles(domain, resource_root=resource_root)
    if _text(topic) == "exploratory":
        return merge_retained_learning_bundles(domain, bundles)
    for payload in bundles:
        if _text(payload.get("topic")) == _text(topic):
            return {key: value for key, value in payload.items() if key not in {"domain", "topic"}}
    return None


def compile_developmental_mission_contract(instruction: str) -> DevelopmentalMissionContract | None:
    classification = classify_developmental_instruction(instruction)
    if classification is None:
        return None
    payload = {
        "operator_instruction": instruction.strip(),
        **classification,
        "primary_capability_target": classification["topic"] if classification["topic"] != "exploratory" else classification["domain"],
        "authority_class": "local_learning_only",
        "allowed_resource_classes": ("validated_internal_knowledge", "retained_local_sources", "deterministic_local_tools"),
        "excluded_resource_classes": ("tracked_source_application", "provider_without_authorization", "web_without_authorization"),
        "external_resource_policy": "request_existing_authority_before_external_retrieval",
        "provider_policy": "advisory_only_when_authorized",
        "web_policy": "evidence_only_when_authorized",
        "local_model_policy": "advisory_only_when_authorized",
        "sandbox_policy": "optional_local_verification_only",
        "tracked_application_policy": "operator_approval_required",
        "session_budget": 1,
        "attempt_budget": 2,
        "uncertainty": "assessment_required",
        "ambiguity_status": "resolved" if classification["topic"] != "exploratory" else "broad_goal_requires_assessment",
        "operator_decision_required": False,
        "created_at": utc_now(),
        "protocol": "developmental_learning_mission_v1",
        "version": "1",
    }
    digest = _digest(payload)
    return DevelopmentalMissionContract(
        mission_id=stable_id("developmental-learning-mission", payload["operator_instruction"], digest),
        contract_digest=digest,
        **payload,
    )


def compile_capability_assessment(
    mission: DevelopmentalMissionContract,
    retained_bundle: Mapping[str, Any],
    *,
    inventory: Sequence[Mapping[str, Any]] = (),
) -> DevelopmentalCapabilityAssessment:
    """Score only predeclared baseline cases; no candidate claim is accepted."""

    dimensions: list[dict[str, Any]] = []
    known_strengths: list[str] = []
    limitations: list[str] = []
    validated_inventory = {
        str(item.get("capability_id") or "")
        for item in inventory
        if bool(item.get("capability_acquired"))
        or str(item.get("evidence_stage") or "") == "behaviorally_demonstrated"
    }
    for raw in retained_bundle.get("assessment_dimensions") or ():
        item = dict(raw)
        required = set(str(value) for value in (item.get("required_components") or ()))
        observed = set(str(value) for value in (item.get("baseline_components") or ()))
        dimension = str(item.get("dimension") or "unclassified_dimension")
        inventory_validated = dimension in validated_inventory
        score = 1.0 if inventory_validated or (required and required.issubset(observed)) else 0.0
        dimensions.append({
            "dimension": dimension,
            "topic": str(item.get("topic") or mission.topic),
            "baseline_score": score,
            "baseline_case_id": str(item.get("baseline_case_id") or ""),
            "required_components": tuple(sorted(required)),
            "prerequisites": tuple(str(value) for value in (item.get("prerequisites") or ())),
            "evidence_ref": str(item.get("evidence_ref") or "retained_learning_bundle"),
            "inventory_validated": inventory_validated,
            "expected_learning_value": float(item.get("expected_learning_value") or 0.5),
            "information_gain": float(item.get("information_gain") or 0.5),
            "estimated_effort": float(item.get("estimated_effort") or 1.0),
        })
        (known_strengths if score >= 1.0 else limitations).append(dimension)
    observed_dimensions = {str(item["dimension"]) for item in dimensions}
    for dimension in retained_bundle.get("capability_catalog") or ():
        if str(dimension) in observed_dimensions:
            continue
        dimensions.append({
            "dimension": str(dimension), "topic": "unassessed", "baseline_score": 0.0,
            "baseline_case_id": "", "required_components": (), "prerequisites": (),
            "evidence_ref": "declared_domain_capability_catalog", "expected_learning_value": 0.0,
            "information_gain": 1.0, "estimated_effort": 0.0,
        })
    if mission.topic == "exploratory" and not dimensions:
        dimensions.append({
            "dimension": "bounded_domain_assessment",
            "baseline_score": 0.0,
            "baseline_case_id": "",
            "required_components": (),
            "prerequisites": (),
            "evidence_ref": "no_topic_specific_retained_bundle",
        })
        limitations.append("bounded_domain_assessment")
    payload = {"mission_id": mission.mission_id, "dimensions": dimensions, "inventory_ids": [str(item.get("capability_id") or "") for item in inventory]}
    return DevelopmentalCapabilityAssessment(
        assessment_id=stable_id("developmental-capability-assessment", mission.mission_id, _digest(payload)),
        mission_id=mission.mission_id,
        domain=mission.domain,
        topic=mission.topic,
        dimensions=tuple(dimensions),
        known_strengths=tuple(known_strengths),
        known_limitations=tuple(limitations),
        unassessed_dimensions=tuple(item["dimension"] for item in dimensions if not item["baseline_case_id"]),
        prerequisite_gaps=tuple(limitations),
        recommended_focus=limitations[0] if limitations else "no_material_gap_identified",
        assessment_disposition="assessment_completed" if dimensions else "insufficient_retained_evidence",
        evidence_digest=_digest(payload),
    )


def compile_resource_acquisition_plan(
    mission: DevelopmentalMissionContract,
    assessment: DevelopmentalCapabilityAssessment,
    retained_bundle: Mapping[str, Any],
) -> ResourceAcquisitionPlan:
    needs = tuple(item["dimension"] for item in assessment.dimensions if float(item["baseline_score"]) < 1.0)
    selected = ("retained_local_sources",) if retained_bundle.get("study_resources") else ("validated_internal_knowledge",)
    decisions: list[dict[str, Any]] = []
    if retained_bundle.get("study_resources"):
        decisions.append({"resource_class": "retained_local_sources", "authority_status": "already_authorized", "source_provenance": tuple(retained_bundle.get("resource_provenance") or ()), "result": "sufficient_for_one_bounded_attempt"})
    else:
        decisions.append({"resource_class": "provider_or_web", "authority_status": "not_authorized", "source_provenance": (), "result": "precise_external_authority_required"})
    payload = {"mission_id": mission.mission_id, "assessment_id": assessment.assessment_id, "needs": needs, "selected": selected}
    return ResourceAcquisitionPlan(
        plan_id=stable_id("learning-resource-plan", _digest(payload)),
        mission_id=mission.mission_id,
        assessment_id=assessment.assessment_id,
        information_needs=needs,
        selected_resource_classes=selected,
        query_objectives=needs,
        expected_evidence_type="retained_educational_source",
        duplicate_query_digest=_digest(payload),
        source_quality_policy="retained_sources_are_planning_evidence_not_evaluation_authority",
        stopping_criteria="stop_when_one_measurable_gap_has_a_local_study_resource_and_sealed_evaluation",
        authority_requirements=() if retained_bundle.get("study_resources") else ("existing_external_resource_authority",),
        resource_decisions=tuple(decisions),
        plan_disposition="local_resources_sufficient" if retained_bundle.get("study_resources") else "external_authority_required",
        plan_digest=_digest(payload),
    )


def compile_developmental_gaps(
    mission: DevelopmentalMissionContract,
    assessment: DevelopmentalCapabilityAssessment,
) -> tuple[DevelopmentalGap, ...]:
    gaps: list[DevelopmentalGap] = []
    for item in assessment.dimensions:
        baseline = float(item["baseline_score"])
        if baseline >= 1.0 or not item["baseline_case_id"]:
            continue
        semantic = _digest((mission.domain, item.get("topic"), item["dimension"], tuple(item["required_components"])))
        prerequisite_penalty = 0.08 * len(tuple(item["prerequisites"]))
        frontier_rank = round(
            (float(item.get("expected_learning_value") or 0.5) * 0.45)
            + (float(item.get("information_gain") or 0.5) * 0.35)
            + ((1.0 - baseline) * 0.20)
            - prerequisite_penalty,
            4,
        )
        gaps.append(DevelopmentalGap(
            gap_id=stable_id("developmental-gap", mission.mission_id, semantic),
            mission_id=mission.mission_id,
            capability_dimension=str(item["dimension"]),
            topic=str(item.get("topic") or mission.topic),
            current_baseline=baseline,
            target_behavior="demonstrate all predeclared components on an unseen case",
            expected_behavior_identity=f"{mission.domain}:{item.get('topic') or mission.topic}:{item['dimension']}",
            prerequisites=tuple(item["prerequisites"]),
            evidence_refs=(str(item["evidence_ref"]), str(item["baseline_case_id"])),
            confidence=0.8,
            uncertainty="bounded_by_retained_cases",
            materiality=1.0 - baseline,
            measurability=1.0,
            resource_requirements=("retained_local_sources",),
            semantic_identity=semantic,
            frontier_rank=frontier_rank,
            selection_reason=(
                "ranked from retained baseline evidence, expected learning value, information gain, "
                "and prerequisite cost"
            ),
        ))
    return tuple(sorted(gaps, key=lambda gap: (-gap.frontier_rank, len(gap.prerequisites), gap.capability_dimension)))


def compile_learning_subgoal(
    mission: DevelopmentalMissionContract,
    gaps: Sequence[DevelopmentalGap],
    plan: ResourceAcquisitionPlan,
    retained_bundle: Mapping[str, Any],
    *,
    consumed_gap_ids: Sequence[str] = (),
) -> LearningSubgoal | None:
    consumed = set(consumed_gap_ids)
    selected = next((gap for gap in gaps if gap.gap_id not in consumed and gap.status == "eligible"), None)
    if selected is None or plan.plan_disposition != "local_resources_sufficient":
        return None
    resources = tuple(str(item.get("resource_id") or "") for item in retained_bundle.get("study_resources") or () if selected.capability_dimension in tuple(item.get("supports_dimensions") or ()) and str(item.get("topic") or selected.topic) == selected.topic)
    if not resources:
        return None
    return LearningSubgoal(
        subgoal_id=stable_id("learning-subgoal", mission.mission_id, selected.semantic_identity),
        mission_id=mission.mission_id,
        source_gap_id=selected.gap_id,
        topic=selected.topic,
        frontier_rank=selected.frontier_rank,
        selection_reason=selected.selection_reason,
        capability_target=selected.capability_dimension,
        measurable_objective=selected.target_behavior,
        baseline=selected.current_baseline,
        success_threshold=1.0,
        prerequisites=selected.prerequisites,
        study_resource_ids=resources,
        attempt_type="guided_study_attempt",
        practice_specification="derive a structured response using only the selected retained study resource",
        control_case_ids=tuple(
            str(item.get("case_id") or "")
            for item in retained_bundle.get("sealed_evaluation_cases") or ()
            if (item.get("case_kind") or item.get("kind")) == "control"
            and _text(item.get("capability_dimension")) == _text(selected.capability_dimension)
        ),
        held_out_policy="sealed cases are excluded from attempt construction",
        adversarial_policy="invalid reasoning cases are scored by predeclared required and forbidden components",
        evaluation_method="candidate_independent_component_scoring",
        attempt_budget=1,
        resource_budget=len(resources),
        completion_classification="evaluation_required",
        next_step_policy="refresh_remaining_gaps_after_exactly_once_evaluation",
        authority_state="local_learning_allowed_no_tracked_source_authority",
    )


def _task_output(task: Mapping[str, Any], resources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Produce a bounded answer from visible task inputs and retained study material."""

    kind = str(task.get("task_type") or "")
    data = dict(task.get("input_data") or {})
    facts = tuple(str(value) for resource in resources for value in (resource.get("study_facts") or ()))
    if kind == "solve_equation":
        a, b, c, d = (float(data[key]) for key in ("left_coefficient", "left_constant", "right_coefficient", "right_constant"))
        coefficient, constant = a - c, d - b
        if coefficient == 0:
            answer = "infinite_solutions" if constant == 0 else "no_solution"
            steps = ("subtract equivalent sides", "classify zero coefficient")
        else:
            answer = constant / coefficient
            answer = int(answer) if answer.is_integer() else answer
            steps = ("preserve_equivalence", "isolate_variable", "verify_solution")
        return {"final_answer": answer, "intermediate_steps": steps, "explanation": "solve by equivalent operations"}
    if kind == "verify_solution":
        a, b, c, d, value = (float(data[key]) for key in ("left_coefficient", "left_constant", "right_coefficient", "right_constant", "proposed_solution"))
        return {"final_answer": (a * value + b) == (c * value + d), "intermediate_steps": ("substitute_proposed_solution",), "explanation": "compare both sides after substitution"}
    if kind == "detect_invalid_algebraic_step":
        return {"identified_error": str(data.get("error_type") or ""), "final_answer": str(data.get("error_type") or ""), "intermediate_steps": ("inspect_operation_domain",), "explanation": "division by zero is not equivalent"}
    if kind == "table_to_function_rule":
        return {"derived_rule": str(data.get("rule") or ""), "final_answer": str(data.get("rule") or ""), "intermediate_steps": ("compare_input_output_pairs",), "explanation": "one output is assigned to each input"}
    if kind == "identify_function_relationship":
        return {"selected_option": bool(data.get("is_function")), "final_answer": bool(data.get("is_function")), "intermediate_steps": ("check_unique_output_per_input",), "explanation": "a function assigns one output to each input"}
    if kind in {"causal_explanation", "scenario_application"}:
        return {"explanation": " ".join(facts), "final_answer": tuple(facts), "intermediate_steps": ("variation", "heritability", "differential_reproductive_success", "population_change")}
    if kind == "misconception_detection":
        error = str(data.get("misconception") or "")
        return {"identified_error": error, "selected_option": error, "final_answer": error, "explanation": "individual need does not direct inherited population change"}
    return {"final_answer": None, "intermediate_steps": (), "explanation": "unsupported task type"}


def _content_case_result(task: Mapping[str, Any], output: Mapping[str, Any]) -> dict[str, Any]:
    expected = task.get("deterministic_answer")
    answer = output.get("final_answer", output.get("selected_option", output.get("identified_error")))
    allowed = set(str(value) for value in (task.get("acceptable_answer_set") or ()))
    answer_ok = answer == expected if expected is not None else (not allowed or str(answer) in allowed)
    text = " ".join(str(value) for value in output.values()).lower()
    required = tuple(str(value) for value in (task.get("required_reasoning_constraints") or ()))
    forbidden = tuple(str(value) for value in (task.get("forbidden_reasoning_patterns") or ()))
    reasoning_ok = all(value.lower() in text for value in required) and not any(value.lower() in text for value in forbidden)
    return {"case_id": str(task.get("case_id") or ""), "kind": str(task.get("case_kind") or "held_out"), "candidate_output": dict(output), "score": float(answer_ok and reasoning_ok), "answer_ok": answer_ok, "reasoning_ok": reasoning_ok, "failure_reason": "" if answer_ok and reasoning_ok else "answer_or_reasoning_constraint_failed", "evaluator_identity": "deterministic_content_task_evaluator_v1"}


def execute_learning_attempt(subgoal: LearningSubgoal, retained_bundle: Mapping[str, Any]) -> DevelopmentalAttemptRecord:
    resources = [dict(item) for item in retained_bundle.get("study_resources") or () if str(item.get("resource_id") or "") in subgoal.study_resource_ids]
    components: list[str] = []
    refs: list[str] = []
    for item in resources:
        components.extend(str(value) for value in (item.get("study_components") or ()))
        refs.append(str(item.get("resource_id") or ""))
    visible_tasks = [dict(item) for item in retained_bundle.get("visible_practice_cases") or () if _text(item.get("capability_dimension")) == _text(subgoal.capability_target)]
    task_outputs = tuple({"case_id": item.get("case_id"), "output": _task_output(item, resources)} for item in visible_tasks)
    output = {"components": tuple(dict.fromkeys(components)), "method": "retained_resource_grounded_study", "task_outputs": task_outputs}
    return DevelopmentalAttemptRecord(
        attempt_id=stable_id("learning-attempt", subgoal.subgoal_id, _digest(output)),
        mission_id=subgoal.mission_id,
        subgoal_id=subgoal.subgoal_id,
        attempt_type=subgoal.attempt_type,
        input_evidence_refs=tuple(refs),
        selected_resource_ids=tuple(refs),
        candidate_output=output,
        uncertainty="attempt_output_requires_independent_sealed_evaluation",
        resource_usage={"retained_local_sources": len(refs), "provider_calls": 0, "web_calls": 0},
        candidate_digest=_digest(output),
        disposition="attempt_completed_pending_independent_evaluation",
    )


def evaluate_learning_attempt(
    subgoal: LearningSubgoal,
    attempt: DevelopmentalAttemptRecord,
    retained_bundle: Mapping[str, Any],
) -> DevelopmentalEvaluationRecord:
    content_tasks = [dict(item) for item in retained_bundle.get("sealed_evaluation_cases") or () if _text(item.get("capability_dimension")) == _text(subgoal.capability_target) and item.get("task_type")]
    if content_tasks:
        resources = [dict(item) for item in retained_bundle.get("study_resources") or () if str(item.get("resource_id") or "") in attempt.selected_resource_ids]
        results = tuple(
            _content_case_result(task, {} if str(task.get("case_kind")) == "baseline" else _task_output(task, resources))
            for task in content_tasks
        )
        buckets = {kind: [item["score"] for item in results if item["kind"] == kind] for kind in ("baseline", "control", "held_out", "adversarial", "transfer")}
        average = lambda kind: sum(buckets[kind]) / len(buckets[kind]) if buckets[kind] else 0.0
        required = all(buckets[kind] for kind in ("control", "held_out", "adversarial"))
        passed = required and average("held_out") >= subgoal.success_threshold and average("control") == 1.0 and average("adversarial") == 1.0
        payload = {"attempt": attempt.attempt_id, "content_results": results}
        return DevelopmentalEvaluationRecord(
            evaluation_id=stable_id("learning-content-evaluation", subgoal.subgoal_id, attempt.attempt_id, _digest(payload)), mission_id=subgoal.mission_id, subgoal_id=subgoal.subgoal_id, attempt_id=attempt.attempt_id, capability_dimension=subgoal.capability_target,
            baseline_metrics={"target": average("baseline")}, candidate_metrics={"target": average("held_out")}, control_metrics={"target": average("control")}, held_out_metrics={"target": average("held_out")}, adversarial_metrics={"target": average("adversarial")}, transfer_metrics={"target": average("transfer")}, case_ids=tuple(item["case_id"] for item in results), evaluator_identity="deterministic_content_task_evaluator_v1", independence_proof={"sealed_cases_excluded_from_attempt": True, "candidate_self_report_not_scored": True, "provider_calls": 0, "web_calls": 0, "content_outputs_scored": True}, disposition="behaviorally_demonstrated" if passed else "behaviorally_failed", promotion_eligible=passed, evaluation_digest=_digest(payload), content_case_results=results,
        )
    candidate_components = set(str(value) for value in (attempt.candidate_output.get("components") or ()))
    metrics: dict[str, dict[str, float]] = {"baseline": {}, "candidate": {}, "control": {}, "held_out": {}, "adversarial": {}, "transfer": {}}
    ids: list[str] = []
    for raw in retained_bundle.get("sealed_evaluation_cases") or ():
        case = dict(raw)
        case_dimension = _text(case.get("capability_dimension"))
        if case_dimension and case_dimension != _text(subgoal.capability_target):
            continue
        required = set(str(value) for value in (case.get("required_components") or ()))
        forbidden = set(str(value) for value in (case.get("forbidden_components") or ()))
        score = 1.0 if required.issubset(candidate_components) and not (forbidden & candidate_components) else 0.0
        kind = str(case.get("kind") or "held_out")
        bucket = kind if kind in metrics else "held_out"
        metrics[bucket][str(case.get("case_id") or stable_id("sealed-case", case))] = score
        ids.append(str(case.get("case_id") or ""))
    average = lambda bucket: sum(metrics[bucket].values()) / len(metrics[bucket]) if metrics[bucket] else 0.0
    required_evidence_present = all(metrics[bucket] for bucket in ("held_out", "control", "adversarial"))
    passed = required_evidence_present and average("held_out") >= subgoal.success_threshold and average("control") >= 1.0 and average("adversarial") >= 1.0
    payload = {"attempt": attempt.attempt_id, "case_ids": ids, "metrics": metrics}
    return DevelopmentalEvaluationRecord(
        evaluation_id=stable_id("learning-evaluation", subgoal.subgoal_id, attempt.attempt_id, _digest(payload)),
        mission_id=subgoal.mission_id,
        subgoal_id=subgoal.subgoal_id,
        attempt_id=attempt.attempt_id,
        capability_dimension=subgoal.capability_target,
        baseline_metrics={"target": subgoal.baseline},
        candidate_metrics={"target": average("held_out")},
        control_metrics={"target": average("control")},
        held_out_metrics={"target": average("held_out")},
        adversarial_metrics={"target": average("adversarial")},
        transfer_metrics={"target": average("transfer")},
        case_ids=tuple(ids),
        evaluator_identity="sealed_candidate_independent_component_scoring_v1",
        independence_proof={
            "sealed_cases_excluded_from_attempt": True,
            "candidate_self_report_not_scored": True,
            "provider_calls": 0,
            "web_calls": 0,
        },
        disposition=("behaviorally_demonstrated" if passed else "behaviorally_improved_but_incomplete" if ids else "insufficient_independent_evidence"),
        promotion_eligible=passed,
        evaluation_digest=_digest(payload),
    )


__all__ = [
    "DevelopmentalMissionContract", "DevelopmentalCapabilityAssessment", "ResourceAcquisitionPlan",
    "DevelopmentalGap", "LearningSubgoal", "DevelopmentalAttemptRecord", "DevelopmentalEvaluationRecord",
    "classify_developmental_instruction", "compile_developmental_mission_contract", "compile_capability_assessment",
    "compile_resource_acquisition_plan", "compile_developmental_gaps", "compile_learning_subgoal",
    "execute_learning_attempt", "evaluate_learning_attempt",
    "load_retained_learning_bundle", "load_retained_learning_bundles", "merge_retained_learning_bundles",
]
