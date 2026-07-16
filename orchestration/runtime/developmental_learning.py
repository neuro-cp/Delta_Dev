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
    plan_disposition: str
    plan_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalGap:
    gap_id: str
    mission_id: str
    capability_dimension: str
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
    status: str = "eligible"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LearningSubgoal:
    subgoal_id: str
    mission_id: str
    source_gap_id: str
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

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_developmental_instruction(instruction: str) -> dict[str, str] | None:
    """Classify a small, explicit learning-intent surface without model authority."""

    normalized = _text(instruction)
    if not any(token in normalized for token in ("learn", "study", "understand", "practice")):
        return None
    domain = "mathematics" if any(token in normalized for token in ("math", "mathematics", "induction", "algebra", "calculus")) else "general_learning"
    topic = "mathematical_induction" if "induction" in normalized else "exploratory"
    return {
        "mission_type": "developmental_learning",
        "domain": domain,
        "topic": topic,
        "mission_mode": "bounded_learning_session" if topic != "exploratory" else "capability_assessment_then_learning",
    }


def load_retained_learning_bundle(domain: str, topic: str, *, resource_root: str | Path | None = None) -> dict[str, Any] | None:
    """Load a retained local resource by declared domain/topic, never by model output."""

    root = Path(resource_root) if resource_root else Path(__file__).resolve().parents[2] / "docs" / "learning_resources"
    if not root.exists():
        return None
    domain_matches: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _text(payload.get("domain")) != _text(domain):
            continue
        cleaned = {key: value for key, value in payload.items() if key not in {"domain", "topic"}}
        if _text(payload.get("topic")) == _text(topic):
            return cleaned
        domain_matches.append(cleaned)
    return domain_matches[0] if _text(topic) == "exploratory" and domain_matches else None


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
    for raw in retained_bundle.get("assessment_dimensions") or ():
        item = dict(raw)
        required = set(str(value) for value in (item.get("required_components") or ()))
        observed = set(str(value) for value in (item.get("baseline_components") or ()))
        score = 1.0 if required and required.issubset(observed) else 0.0
        dimension = str(item.get("dimension") or "unclassified_dimension")
        dimensions.append({
            "dimension": dimension,
            "baseline_score": score,
            "baseline_case_id": str(item.get("baseline_case_id") or ""),
            "required_components": tuple(sorted(required)),
            "prerequisites": tuple(str(value) for value in (item.get("prerequisites") or ())),
            "evidence_ref": str(item.get("evidence_ref") or "retained_learning_bundle"),
        })
        (known_strengths if score >= 1.0 else limitations).append(dimension)
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
        authority_requirements=(),
        plan_disposition="local_resources_sufficient" if retained_bundle.get("study_resources") else "resource_evidence_needed",
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
        semantic = _digest((mission.domain, mission.topic, item["dimension"], tuple(item["required_components"])))
        gaps.append(DevelopmentalGap(
            gap_id=stable_id("developmental-gap", mission.mission_id, semantic),
            mission_id=mission.mission_id,
            capability_dimension=str(item["dimension"]),
            current_baseline=baseline,
            target_behavior="demonstrate all predeclared components on an unseen case",
            expected_behavior_identity=f"{mission.domain}:{mission.topic}:{item['dimension']}",
            prerequisites=tuple(item["prerequisites"]),
            evidence_refs=(str(item["evidence_ref"]), str(item["baseline_case_id"])),
            confidence=0.8,
            uncertainty="bounded_by_retained_cases",
            materiality=1.0 - baseline,
            measurability=1.0,
            resource_requirements=("retained_local_sources",),
            semantic_identity=semantic,
        ))
    return tuple(sorted(gaps, key=lambda gap: (-gap.materiality, len(gap.prerequisites), gap.capability_dimension)))


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
    resources = tuple(str(item.get("resource_id") or "") for item in retained_bundle.get("study_resources") or () if selected.capability_dimension in tuple(item.get("supports_dimensions") or ()))
    if not resources:
        return None
    return LearningSubgoal(
        subgoal_id=stable_id("learning-subgoal", mission.mission_id, selected.semantic_identity),
        mission_id=mission.mission_id,
        source_gap_id=selected.gap_id,
        capability_target=selected.capability_dimension,
        measurable_objective=selected.target_behavior,
        baseline=selected.current_baseline,
        success_threshold=1.0,
        prerequisites=selected.prerequisites,
        study_resource_ids=resources,
        attempt_type="guided_study_attempt",
        practice_specification="derive a structured response using only the selected retained study resource",
        control_case_ids=tuple(str(item.get("case_id") or "") for item in retained_bundle.get("sealed_evaluation_cases") or () if item.get("kind") == "control"),
        held_out_policy="sealed cases are excluded from attempt construction",
        adversarial_policy="invalid reasoning cases are scored by predeclared required and forbidden components",
        evaluation_method="candidate_independent_component_scoring",
        attempt_budget=1,
        resource_budget=len(resources),
        completion_classification="evaluation_required",
        next_step_policy="refresh_remaining_gaps_after_exactly_once_evaluation",
        authority_state="local_learning_allowed_no_tracked_source_authority",
    )


def execute_learning_attempt(subgoal: LearningSubgoal, retained_bundle: Mapping[str, Any]) -> DevelopmentalAttemptRecord:
    resources = [dict(item) for item in retained_bundle.get("study_resources") or () if str(item.get("resource_id") or "") in subgoal.study_resource_ids]
    components: list[str] = []
    refs: list[str] = []
    for item in resources:
        components.extend(str(value) for value in (item.get("study_components") or ()))
        refs.append(str(item.get("resource_id") or ""))
    output = {"components": tuple(dict.fromkeys(components)), "method": "retained_resource_grounded_study"}
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
    "load_retained_learning_bundle",
]
