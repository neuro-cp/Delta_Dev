"""Compile independent evaluation plans for bounded developmental capabilities.

This module owns no execution, curriculum, capability inventory, or persistence.
It translates a controller-owned capability target into an inspectable evaluation
requirement and chooses only from already available evaluator authorities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id


STRATEGIES = (
    "deterministic_predicate",
    "sandbox_behavioral_execution",
    "authoritative_answer_key",
    "simulation_or_model",
    "independent_source_comparison",
    "operator_supplied_sealed_cases",
    "evaluation_unavailable",
)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _words(*values: Any) -> str:
    return " ".join(str(value or "").replace("_", " ").lower() for value in values)


@dataclass(frozen=True)
class CapabilityEvaluationRequirement:
    requirement_id: str
    mission_id: str
    capability_id: str
    subgoal_id: str
    domain: str
    topic: str
    capability_type: str
    target_behavior: str
    observable_outputs: tuple[str, ...]
    correctness_properties: tuple[str, ...]
    boundary_conditions: tuple[str, ...]
    adversarial_requirements: tuple[str, ...]
    transfer_requirements: tuple[str, ...]
    determinism_level: str
    execution_required: bool
    authoritative_reference_required: bool
    simulation_required: bool
    source_independence_required: bool
    answer_key_required: bool
    operator_sealed_cases_allowed: bool
    teaching_evidence_ids: tuple[str, ...]
    excluded_evaluator_sources: tuple[str, ...]
    confidence: float
    uncertainty: str
    semantic_identity: str
    requirement_digest: str
    status: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluatorStrategyCandidate:
    candidate_id: str
    requirement_id: str
    strategy: str
    available: bool
    independence_valid: bool
    rank: float
    reason: str
    evaluator_identity: str
    evaluator_provenance: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    semantic_identity: str
    candidate_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityEvaluationPlan:
    plan_id: str
    requirement_id: str
    selected_strategy: str
    evaluator_identity: str
    evaluator_provenance: tuple[str, ...]
    baseline_policy: str
    control_policy: str
    held_out_policy: str
    adversarial_policy: str
    transfer_policy: str
    failure_localization_policy: str
    capability_update_policy: str
    sandbox_scope: str
    tracked_source_mutation_allowed: bool
    status: str
    plan_digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_capability_type(
    *,
    domain: str,
    topic: str,
    capability_target: str,
    target_behavior: str,
    execution_kind: str = "",
) -> str:
    """Classify from observable characteristics, never from a desired strategy."""

    text = _words(domain, topic, capability_target, target_behavior, execution_kind)
    if any(token in text for token in ("repository", "patch", "software", "callable", "runtime behavior")):
        return "software_behavior"
    if any(token in text for token in ("source comparison", "evidence synthesis", "provenance", "contradiction", "sourced")):
        return "evidence_synthesis"
    if any(token in text for token in ("matrix", "equation", "algebra", "spectral", "induction", "mathematical")):
        return "mathematical_reasoning"
    if any(token in text for token in ("mechanism", "causal", "selection", "predict")):
        return "causal_explanation"
    if any(token in text for token in ("classify", "detect", "recognition")):
        return "classification_or_detection"
    if any(token in text for token in ("execute", "procedure", "transform")):
        return "procedural_execution"
    if any(token in text for token in ("relation", "distinguish", "semantic")):
        return "relational_semantic"
    if capability_target or target_behavior:
        return "declarative_concept"
    return "unknown"


def compile_capability_evaluation_requirement(
    *,
    mission_id: str,
    capability_id: str,
    subgoal_id: str,
    domain: str,
    topic: str,
    capability_target: str,
    target_behavior: str,
    teaching_evidence_ids: Sequence[str] = (),
    execution_kind: str = "",
    capability_context: Mapping[str, Any] | None = None,
) -> CapabilityEvaluationRequirement:
    context = dict(capability_context or {})
    capability_type = classify_capability_type(
        domain=domain, topic=topic, capability_target=capability_target,
        target_behavior=target_behavior, execution_kind=execution_kind,
    )
    execution_required = capability_type in {"software_behavior", "procedural_execution"}
    source_independence_required = capability_type == "evidence_synthesis"
    answer_key_required = capability_type in {"declarative_concept", "causal_explanation", "relational_semantic"}
    deterministic = capability_type in {"mathematical_reasoning", "classification_or_detection"}
    semantic = _digest({
        "domain": domain, "topic": topic, "target": capability_target,
        "behavior": target_behavior, "type": capability_type,
        "teaching": tuple(sorted(str(item) for item in teaching_evidence_ids)),
        "context": {key: context[key] for key in sorted(context) if key in {"required_scope", "authority_scope", "execution_kind"}},
    })
    payload = {
        "mission_id": mission_id, "capability_id": capability_id, "subgoal_id": subgoal_id,
        "type": capability_type, "semantic": semantic,
    }
    return CapabilityEvaluationRequirement(
        requirement_id=stable_id("capability-evaluation-requirement", semantic),
        mission_id=mission_id, capability_id=capability_id, subgoal_id=subgoal_id,
        domain=domain, topic=topic, capability_type=capability_type,
        target_behavior=target_behavior,
        observable_outputs=("typed candidate output", "independent scored result"),
        correctness_properties=("predeclared correctness predicate", "teaching source cannot self-certify"),
        boundary_conditions=(str(context.get("required_scope") or "declared capability scope"),),
        adversarial_requirements=("predeclared adversarial case or invalid-input boundary",),
        transfer_requirements=("unseen case from the same declared scope",),
        determinism_level="deterministic_required" if deterministic else "independent_authority_required",
        execution_required=execution_required,
        authoritative_reference_required=not execution_required,
        simulation_required=False,
        source_independence_required=source_independence_required,
        answer_key_required=answer_key_required,
        operator_sealed_cases_allowed=True,
        teaching_evidence_ids=tuple(sorted(str(item) for item in teaching_evidence_ids)),
        excluded_evaluator_sources=tuple(sorted(str(item) for item in teaching_evidence_ids)),
        confidence=0.8 if capability_type != "unknown" else 0.3,
        uncertainty="evaluator authority must be selected independently of teaching evidence",
        semantic_identity=semantic,
        requirement_digest=_digest(payload),
        status="requirement_compiled",
    )


def _candidate(
    requirement: CapabilityEvaluationRequirement,
    *,
    strategy: str,
    available: bool,
    evaluator_identity: str,
    provenance: Sequence[str] = (),
    rejection_reasons: Sequence[str] = (),
    rank: float = 0.0,
    reason: str,
) -> EvaluatorStrategyCandidate:
    conflicts = set(requirement.excluded_evaluator_sources).intersection(str(item) for item in provenance)
    rejected = tuple(dict.fromkeys(tuple(str(item) for item in rejection_reasons) + (("teaching_source_conflict",) if conflicts else ())))
    independence_valid = bool(available and evaluator_identity and not rejected)
    payload = {"requirement": requirement.requirement_id, "strategy": strategy, "identity": evaluator_identity, "provenance": tuple(provenance), "rejected": rejected}
    return EvaluatorStrategyCandidate(
        candidate_id=stable_id("capability-evaluation-strategy", _digest(payload)),
        requirement_id=requirement.requirement_id, strategy=strategy,
        available=available, independence_valid=independence_valid,
        rank=rank if independence_valid else 0.0, reason=reason,
        evaluator_identity=evaluator_identity, evaluator_provenance=tuple(str(item) for item in provenance),
        rejection_reasons=rejected, semantic_identity=_digest(payload), candidate_digest=_digest(payload),
    )


def compile_strategy_candidates(
    requirement: CapabilityEvaluationRequirement,
    *,
    evaluator_authorities: Sequence[Mapping[str, Any]] = (),
) -> tuple[EvaluatorStrategyCandidate, ...]:
    authorities = [dict(item) for item in evaluator_authorities]
    def find(kind: str) -> list[dict[str, Any]]:
        return [item for item in authorities if str(item.get("strategy") or "") == kind]
    def best(kind: str) -> dict[str, Any] | None:
        items = find(kind)
        return items[0] if items else None

    def authority_rejections(authority: Mapping[str, Any] | None) -> tuple[str, ...]:
        if authority and authority.get("candidate_mutable"):
            return ("candidate_mutable_evaluator",)
        return ()

    candidates: list[EvaluatorStrategyCandidate] = []
    deterministic = best("deterministic_predicate")
    scope_ok = bool(deterministic and (not deterministic.get("scope") or str(deterministic.get("scope")) in requirement.boundary_conditions or requirement.topic in str(deterministic.get("scope"))))
    candidates.append(_candidate(requirement, strategy="deterministic_predicate", available=bool(deterministic and scope_ok), evaluator_identity=str((deterministic or {}).get("identity") or ""), provenance=tuple((deterministic or {}).get("provenance") or ()), rejection_reasons=(authority_rejections(deterministic) if deterministic and scope_ok else ("missing_or_scope_mismatched_deterministic_authority",)), rank=1.0, reason="exact predicate authority is available for the declared scope"))
    sandbox = best("sandbox_behavioral_execution")
    sandbox_available = bool(sandbox and requirement.execution_required and bool(sandbox.get("disposable")))
    candidates.append(_candidate(requirement, strategy="sandbox_behavioral_execution", available=sandbox_available, evaluator_identity=str((sandbox or {}).get("identity") or ""), provenance=tuple((sandbox or {}).get("provenance") or ()), rejection_reasons=(authority_rejections(sandbox) if sandbox_available else ("sandbox_execution_not_required_or_not_disposable",)), rank=0.95, reason="disposable behavioral assertions are available"))
    answer_key = best("authoritative_answer_key")
    answer_available = bool(answer_key and answer_key.get("sealed") and answer_key.get("provenance"))
    candidates.append(_candidate(requirement, strategy="authoritative_answer_key", available=answer_available, evaluator_identity=str((answer_key or {}).get("identity") or ""), provenance=tuple((answer_key or {}).get("provenance") or ()), rejection_reasons=(authority_rejections(answer_key) if answer_available else ("missing_sealed_authoritative_answer_key",)), rank=0.85, reason="sealed answer-key authority is available"))
    simulation = best("simulation_or_model")
    simulation_available = bool(simulation and simulation.get("trusted") and simulation.get("independent"))
    candidates.append(_candidate(requirement, strategy="simulation_or_model", available=simulation_available, evaluator_identity=str((simulation or {}).get("identity") or ""), provenance=tuple((simulation or {}).get("provenance") or ()), rejection_reasons=(authority_rejections(simulation) if simulation_available else ("no_trusted_independent_simulation",)), rank=0.8, reason="trusted independent model is available"))
    source = best("independent_source_comparison")
    source_available = bool(source and requirement.source_independence_required and len(tuple(source.get("provenance") or ())) >= 2 and source.get("contradiction_handling"))
    candidates.append(_candidate(requirement, strategy="independent_source_comparison", available=source_available, evaluator_identity=str((source or {}).get("identity") or ""), provenance=tuple((source or {}).get("provenance") or ()), rejection_reasons=(authority_rejections(source) if source_available else ("independent_source_comparison_not_sufficient_or_not_provenanced",)), rank=0.75, reason="multiple independent sources support a synthesis-only evaluation"))
    candidates.append(_candidate(requirement, strategy="operator_supplied_sealed_cases", available=False, evaluator_identity="operator_sealed_case_authority", rejection_reasons=("operator_cases_not_yet_supplied",), rank=0.0, reason="operator may provide sealed independent cases when automated authority is unavailable"))
    candidates.append(_candidate(requirement, strategy="evaluation_unavailable", available=True, evaluator_identity="", rejection_reasons=(), rank=0.01, reason="terminal honest outcome when no valid independent evaluator is available"))
    return tuple(candidates)


def select_evaluation_plan(
    requirement: CapabilityEvaluationRequirement,
    candidates: Sequence[EvaluatorStrategyCandidate],
) -> tuple[CapabilityEvaluationPlan, dict[str, Any] | None]:
    valid = [candidate for candidate in candidates if candidate.independence_valid and candidate.strategy != "evaluation_unavailable"]
    selected = sorted(valid, key=lambda item: (-item.rank, item.strategy, item.candidate_id))[0] if valid else None
    if selected is None:
        need = {
            "request_id": stable_id("evaluator-authority-request", requirement.semantic_identity),
            "request_type": "operator_supplied_sealed_cases",
            "capability_id": requirement.capability_id,
            "required_behavior": requirement.target_behavior,
            "coverage": ("baseline", "control", "held_out", "adversarial", "transfer"),
            "prohibited": ("teaching_answer_leakage", "candidate_mutable_cases"),
            "status": "evaluator_authority_needed",
        }
        plan = CapabilityEvaluationPlan(
            plan_id=stable_id("capability-evaluation-plan", requirement.semantic_identity, "unavailable"),
            requirement_id=requirement.requirement_id, selected_strategy="evaluation_unavailable",
            evaluator_identity="", evaluator_provenance=(), baseline_policy="no independent baseline authority", control_policy="not executable", held_out_policy="not executable", adversarial_policy="not executable", transfer_policy="not executable",
            failure_localization_policy="persist exact missing evaluator authority", capability_update_policy="promotion_prohibited", sandbox_scope="none", tracked_source_mutation_allowed=False,
            status="evaluation_unavailable", plan_digest=_digest({"requirement": requirement.requirement_id, "status": "unavailable"}),
        )
        return plan, need
    plan = CapabilityEvaluationPlan(
        plan_id=stable_id("capability-evaluation-plan", requirement.semantic_identity, selected.semantic_identity),
        requirement_id=requirement.requirement_id, selected_strategy=selected.strategy,
        evaluator_identity=selected.evaluator_identity, evaluator_provenance=selected.evaluator_provenance,
        baseline_policy="predeclared baseline cases scored by the selected independent authority",
        control_policy="predeclared control cases preserve unrelated behavior",
        held_out_policy="held-out cases remain excluded from attempt construction",
        adversarial_policy="predeclared adversarial cases exercise declared boundary conditions",
        transfer_policy="unseen cases from the declared scope only",
        failure_localization_policy={
            "deterministic_predicate": "failed predicate and implicated concept",
            "sandbox_behavioral_execution": "failed behavioral assertion, runtime error, or artifact mismatch",
            "authoritative_answer_key": "incorrect answer category without answer leakage",
            "independent_source_comparison": "unsupported claim, contradiction, provenance failure, or synthesis omission",
            "simulation_or_model": "model-output mismatch within declared assumptions",
        }.get(selected.strategy, "bounded evaluator failure evidence"),
        capability_update_policy="independent plan must pass before narrow capability update",
        sandbox_scope="disposable_only" if selected.strategy == "sandbox_behavioral_execution" else "not_required",
        tracked_source_mutation_allowed=False,
        status="evaluation_plan_ready", plan_digest=_digest({"requirement": requirement.requirement_id, "candidate": selected.candidate_id}),
    )
    return plan, None


def compile_capability_evaluation_strategy(
    *,
    mission_id: str,
    capability_id: str,
    subgoal_id: str,
    domain: str,
    topic: str,
    capability_target: str,
    target_behavior: str,
    teaching_evidence_ids: Sequence[str] = (),
    execution_kind: str = "",
    capability_context: Mapping[str, Any] | None = None,
    evaluator_authorities: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    requirement = compile_capability_evaluation_requirement(
        mission_id=mission_id, capability_id=capability_id, subgoal_id=subgoal_id,
        domain=domain, topic=topic, capability_target=capability_target,
        target_behavior=target_behavior, teaching_evidence_ids=teaching_evidence_ids,
        execution_kind=execution_kind, capability_context=capability_context,
    )
    candidates = compile_strategy_candidates(requirement, evaluator_authorities=evaluator_authorities)
    plan, authority_request = select_evaluation_plan(requirement, candidates)
    return {
        "requirement": requirement.as_dict(),
        "strategy_candidates": tuple(candidate.as_dict() for candidate in candidates),
        "selected_plan": plan.as_dict(),
        "evaluator_authority_request": authority_request,
    }


__all__ = [
    "STRATEGIES", "CapabilityEvaluationRequirement", "EvaluatorStrategyCandidate", "CapabilityEvaluationPlan",
    "classify_capability_type", "compile_capability_evaluation_requirement", "compile_strategy_candidates",
    "select_evaluation_plan", "compile_capability_evaluation_strategy",
]
