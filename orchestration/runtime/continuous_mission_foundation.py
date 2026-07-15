"""Contracts and pure helpers for continuous DELTA missions.

The authoritative coordinator remains ``continuous_runtime_controller``. This
module deliberately contains no service loop, no heartbeat writer, no process
supervision, no popup launcher, no tracked-source mutation, and no Git action.
It provides immutable records and deterministic helper functions that the
existing controller can consume.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from orchestration.runtime.delta_1_0_common import stable_id, utc_now


PROTECTED_PATH_PATTERNS = ("DELTA-75", "reports/RC4_*")
OBSERVATION_STATE = "runtime_currently_stable_no_immediate_high_value_work"


@dataclass(frozen=True)
class LocalRuntimeAuthority:
    continuous_local_authority: bool = True
    artificial_wall_clock_ceiling: bool = False
    artificial_attempt_ceiling: bool = False
    artificial_test_ceiling: bool = False
    artificial_subprocess_ceiling: bool = False
    artificial_local_disk_policy_ceiling: bool = False
    physical_capacity_still_applies: bool = True
    local_counters_observability_only: bool = True


@dataclass(frozen=True)
class ApiAuthorityState:
    enabled: bool
    allowed_providers: tuple[str, ...] = ()
    allowed_models: tuple[str, ...] = ()
    call_allowance: int | None = None
    token_allowance: int | None = None
    cost_allowance: float | None = None
    calls_consumed: int = 0
    tokens_consumed: int = 0
    reported_cost: str = "unavailable_from_provider_response"
    failures: int = 0
    retries: int = 0
    pending_provider_tasks: tuple[str, ...] = ()
    last_provider_result: str = ""
    unavailability_reason: str = ""


@dataclass(frozen=True)
class BroadMissionContract:
    mission_id: str
    original_operator_goal: str
    normalized_goal: str
    accepted_at: str
    local_authority: LocalRuntimeAuthority
    api_authority: ApiAuthorityState
    tracked_source_application_operator_controlled: bool = True
    commit_push_operator_controlled: bool = True
    protected_paths: tuple[str, ...] = PROTECTED_PATH_PATTERNS
    completion_policy: str = "continuous_runtime_currently_stable_is_observation_not_completion"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeFinding:
    finding_id: str
    evidence_source: str
    observed_behavior: str
    first_incorrect_transition: str
    affected_capability: str
    baseline_metric: str
    confidence: float
    uncertainty: str
    scope: str
    operator_value: float
    severity: float
    estimated_implementation_breadth: str
    validation_method: str
    diagnostic_only: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WeaknessCandidate:
    weakness_id: str
    semantic_signature: str
    description: str
    first_incorrect_transition: str
    source_evidence: tuple[str, ...]
    measurable_target: str
    baseline: str
    controls: tuple[str, ...]
    adversarial_plan: str
    held_out_plan: str
    prerequisites: tuple[str, ...]
    estimated_scope: str
    risk: float
    operator_value: float
    priority: float
    status: str = "eligible"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActiveSubgoal:
    subgoal_id: str
    source_mission_id: str
    weakness_id: str
    measurable_objective: str
    baseline: str
    success_threshold: str
    controls: tuple[str, ...]
    adversarial_tests: str
    held_out_policy: str
    sandbox_scope: str
    source_inspection_scope: tuple[str, ...]
    tracked_application_allowlist: tuple[str, ...]
    rollback_condition: str
    completion_classification: str = "not_started"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityKnowledgeRecord:
    capability_id: str
    original_weakness: str
    evidence: tuple[str, ...]
    first_incorrect_transition: str
    strategies_attempted: tuple[str, ...]
    failed_approaches: tuple[str, ...]
    successful_mechanism: str
    exact_candidate: str
    tests_added: tuple[str, ...]
    metrics_before_after: Mapping[str, Any]
    controls: tuple[str, ...]
    adversarial_evidence: tuple[str, ...]
    held_out_evidence: Mapping[str, Any]
    reproduction_evidence: str
    provider_contribution: str
    local_repair_contribution: str
    application_evidence: str
    regression_evidence: str
    reassessment: str
    residual_uncertainty: str
    reusable_process_rules: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifiedCapability:
    capability_id: str
    category: str
    status: str
    evidence: tuple[str, ...]
    limitations: tuple[str, ...]
    transfer_evidence: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LongHorizonObjective:
    objective_id: str
    original_objective: str
    normalized_objective: str
    scope: str
    values_and_constraints: tuple[str, ...]
    acceptable_methods: tuple[str, ...]
    authority_boundaries: tuple[str, ...]
    success_interpretation: str
    uncertainty: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalCapabilityPlan:
    plan_id: str
    objective_id: str
    capability_inventory: tuple[Mapping[str, Any], ...]
    derived_gap: str
    gap_type: str
    prerequisite_graph: Mapping[str, tuple[str, ...]]
    next_main_goal: str
    next_main_goal_normalized: str
    evidence_basis: tuple[str, ...]
    missing_confidence_questions: tuple[str, ...]
    recommended_resources: tuple[str, ...]
    rejection_conditions: tuple[str, ...]
    hardcoded_rule_denied: str
    authority_boundary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalSelfAssessment:
    assessment_id: str
    objective_id: str
    verified_capabilities: tuple[str, ...]
    assumed_capabilities: tuple[str, ...]
    newly_enabled_possibilities: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    developmental_gaps: tuple[str, ...]
    missing_confidence_questions: tuple[str, ...]
    recommended_resources: tuple[str, ...]
    confidence: float
    needs_additional_insight: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalInsightRequest:
    request_id: str
    objective_id: str
    question: str
    confidence_reason: str
    selected_resource: str
    expected_evidence: str
    authority_boundary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DevelopmentalOperatorExplanation:
    explanation_id: str
    objective_id: str
    current_understanding: str
    verified_abilities: tuple[str, ...]
    assumed_or_unverified_abilities: tuple[str, ...]
    missing_prerequisites: tuple[str, ...]
    next_goal: str
    why_next_goal_matters: str
    uncertainty: str
    authority_boundary: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MainGoalContract:
    main_goal_id: str
    parent_mission_id: str
    original_objective: str
    normalized_objective: str
    success_criteria: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    prerequisite_graph: Mapping[str, tuple[str, ...]]
    known_subgoals: tuple[str, ...]
    active_subgoal: str
    completed_subgoals: tuple[str, ...]
    blocked_subgoals: tuple[str, ...]
    rejected_strategies: tuple[str, ...]
    newly_discovered_prerequisites: tuple[str, ...]
    residual_uncertainty: str
    capability_changes: tuple[str, ...]
    disposition: str
    completion_rationale: str
    next_main_goal_candidates: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compile_broad_mission_contract(
    operator_goal: str,
    *,
    api_authority: ApiAuthorityState | None = None,
) -> BroadMissionContract:
    normalized = "optimize_delta_runtime_continuously"
    if operator_goal.strip().lower().rstrip(".") != "optimize your runtime":
        normalized = "bounded_continuous_runtime_improvement"
    return BroadMissionContract(
        mission_id=stable_id("continuous-mission", operator_goal.strip().lower(), normalized),
        original_operator_goal=operator_goal,
        normalized_goal=normalized,
        accepted_at=utc_now(),
        local_authority=LocalRuntimeAuthority(),
        api_authority=api_authority or ApiAuthorityState(enabled=False, unavailability_reason="not_required_for_foundation_pilot"),
    )


def compile_long_horizon_objective(objective: str) -> LongHorizonObjective:
    normalized = _normalize_development_objective(objective)
    return LongHorizonObjective(
        objective_id=stable_id("long-horizon-objective", objective.strip().lower(), normalized),
        original_objective=objective,
        normalized_objective=normalized,
        scope="developmental_capability_growth",
        values_and_constraints=(
            "evidence-backed capability claims only",
            "local resources preferred before paid providers",
            "tracked-source application remains operator-gated",
            "governance cannot be rewritten by the developmental planner",
        ),
        acceptable_methods=(
            "capability inventory",
            "prerequisite graph derivation",
            "local sandbox construction",
            "exercise generation",
            "held-out and transfer validation",
            "governed reference lookup when confidence is insufficient",
        ),
        authority_boundaries=(
            "no provider authority expansion",
            "no tracked-source mutation",
            "no Git or deployment",
            "no mastery claim without repeated held-out and transfer evidence",
        ),
        success_interpretation="progressive verified capability expansion, not one-shot answer quality",
        uncertainty="long-horizon requirements are provisional until validated by exercises, sources, and transfer tests",
    )


def capability_inventory_from_knowledge(knowledge_ledger: Sequence[CapabilityKnowledgeRecord]) -> tuple[VerifiedCapability, ...]:
    inventory: list[VerifiedCapability] = []
    for record in knowledge_ledger:
        status = "functional" if record.reassessment == "satisfied" else "emerging" if record.reassessment else "unverified"
        category = _capability_category(record.capability_id, record.original_weakness, record.successful_mechanism)
        inventory.append(
            VerifiedCapability(
                capability_id=record.capability_id,
                category=category,
                status=status,
                evidence=tuple(record.evidence) + (record.regression_evidence, record.reproduction_evidence),
                limitations=(record.residual_uncertainty,),
                transfer_evidence=tuple(str(item) for item in record.held_out_evidence.values()) if isinstance(record.held_out_evidence, Mapping) else (),
            )
        )
    return tuple(inventory)


def derive_developmental_capability_plan(
    objective: LongHorizonObjective,
    inventory: Sequence[VerifiedCapability],
) -> DevelopmentalCapabilityPlan:
    assessment = assess_developmental_capability_state(objective, inventory)
    categories = {item.category for item in inventory if item.status in {"functional", "reliable", "transferable"}}
    evidence_basis = tuple(item.capability_id for item in inventory if item.status in {"functional", "reliable", "transferable"})
    required = _objective_requirement_model(objective)
    if required:
        missing = tuple(item for item in required if item not in categories)
        derived_gap = _derived_gap_for_objective(objective, missing)
        next_goal, next_normalized = _next_goal_for_gap(objective, missing)
        return DevelopmentalCapabilityPlan(
            plan_id=stable_id("developmental-plan", objective.objective_id, next_normalized, missing),
            objective_id=objective.objective_id,
            capability_inventory=tuple(item.as_dict() for item in inventory),
            derived_gap=derived_gap,
            gap_type="missing_tooling_and_skill_prerequisites",
            prerequisite_graph={key: tuple(value) for key, value in required.items()},
            next_main_goal=next_goal,
            next_main_goal_normalized=next_normalized,
            evidence_basis=evidence_basis,
            missing_confidence_questions=assessment.missing_confidence_questions,
            recommended_resources=assessment.recommended_resources,
            rejection_conditions=(
                "do not begin domain mastery curriculum before prerequisite capability validation",
                "do not mark reading or explanation as certified capability",
                "do not treat provider suggestions as authorization",
            ),
            hardcoded_rule_denied="derived from objective wording, verified capability inventory, and missing requirement categories; no fixed next-goal sequence",
            authority_boundary="planner may propose next main goal only; execution/application remain controller and LIVE-45 governed",
        )
    return DevelopmentalCapabilityPlan(
        plan_id=stable_id("developmental-plan", objective.objective_id, "capability_inventory_reassessment"),
        objective_id=objective.objective_id,
        capability_inventory=tuple(item.as_dict() for item in inventory),
        derived_gap="insufficient_objective_specific_prerequisite_model",
        gap_type="missing_evidence",
        prerequisite_graph={},
        next_main_goal="Gather governed evidence for prerequisite graph derivation",
        next_main_goal_normalized="prerequisite_evidence_gathering",
        evidence_basis=evidence_basis,
        missing_confidence_questions=("What capability requirements does the long-horizon objective impose?",),
        recommended_resources=("built-in reference retrieval", "local model advisory critique"),
        rejection_conditions=("do not fabricate a module without prerequisite evidence",),
        hardcoded_rule_denied="no static next-goal list used",
        authority_boundary="planner proposes evidence gathering only",
    )


def main_goal_from_developmental_plan(contract: BroadMissionContract, plan: DevelopmentalCapabilityPlan) -> MainGoalContract:
    return MainGoalContract(
        main_goal_id=stable_id("continuous-main-goal", contract.mission_id, plan.next_main_goal_normalized, plan.plan_id),
        parent_mission_id=contract.mission_id,
        original_objective=plan.next_main_goal,
        normalized_objective=plan.next_main_goal_normalized,
        success_criteria=tuple(plan.prerequisite_graph) or ("prerequisite_graph_evidence",),
        evidence_requirements=("capability_inventory", "prerequisite_graph", "validation_environment", "held_out_transfer_plan"),
        prerequisite_graph=plan.prerequisite_graph,
        known_subgoals=(),
        active_subgoal="",
        completed_subgoals=(),
        blocked_subgoals=(),
        rejected_strategies=(),
        newly_discovered_prerequisites=tuple(plan.prerequisite_graph),
        residual_uncertainty="developmental planner output requires governed implementation and validation",
        capability_changes=(),
        disposition="active",
        completion_rationale=f"derived from developmental plan {plan.plan_id}",
        next_main_goal_candidates=(),
    )


def compile_initial_main_goal(contract: BroadMissionContract) -> MainGoalContract:
    long_horizon = compile_long_horizon_objective(contract.original_operator_goal)
    if _is_developmental_direction(contract.original_operator_goal):
        objective = "Develop the ability to understand, explain, and direct my own capability growth"
        criteria = (
            "capability_inventory_generation",
            "long_horizon_gap_analysis",
            "next_developmental_goal_derivation",
            "operator_progress_explanation",
        )
        return MainGoalContract(
            main_goal_id=stable_id("continuous-main-goal", contract.mission_id, objective, criteria),
            parent_mission_id=contract.mission_id,
            original_objective=objective,
            normalized_objective="developmental_self_assessment",
            success_criteria=criteria,
            evidence_requirements=(
                "capability_inventory",
                "long_horizon_objective_record",
                "prerequisite_gap_analysis",
                "next_goal_proposal",
                "operator_readable_progress_summary",
            ),
            prerequisite_graph={
                "capability_inventory_generation": (),
                "long_horizon_gap_analysis": ("capability_inventory_generation",),
                "next_developmental_goal_derivation": ("long_horizon_gap_analysis",),
                "operator_progress_explanation": ("capability_inventory_generation", "next_developmental_goal_derivation"),
            },
            known_subgoals=(),
            active_subgoal="",
            completed_subgoals=(),
            blocked_subgoals=(),
            rejected_strategies=(),
            newly_discovered_prerequisites=("developmental_gap_analysis", "operator_progress_explanation"),
            residual_uncertainty="must prove DELTA can reason from verified capability evidence to the next developmental need",
            capability_changes=(),
            disposition="active",
            completion_rationale="long-horizon growth requires self-assessment, prerequisite planning, and grounded communication before domain pursuit",
            next_main_goal_candidates=("evidence_derived_next_developmental_goal",),
        )
    objective = "Make continuous mission execution real rather than liveness-only"
    criteria = (
        "subgoal_specific_candidate_behavior",
        "resource_usage_result_granularity",
        "application_gate_exercise_coverage",
        "operator_response_bridge",
        "status_write_lock_tolerance",
    )
    return MainGoalContract(
        main_goal_id=stable_id("continuous-main-goal", contract.mission_id, objective, criteria),
        parent_mission_id=contract.mission_id,
        original_objective=objective,
        normalized_objective="real_continuous_mission_execution",
        success_criteria=criteria,
        evidence_requirements=("source_inspection", "sandbox_validation", "clean_reproduction", "operator_boundary_if_needed"),
        prerequisite_graph={item: () for item in criteria},
        known_subgoals=(),
        active_subgoal="",
        completed_subgoals=(),
        blocked_subgoals=(),
        rejected_strategies=(),
        newly_discovered_prerequisites=(),
        residual_uncertainty="not yet assessed",
        capability_changes=(),
        disposition="active",
        completion_rationale="main goal accepted from broad mission",
        next_main_goal_candidates=(),
    )


def capability_satisfies_criterion(record: CapabilityKnowledgeRecord, criterion: str) -> bool:
    if record.reassessment != "satisfied":
        return False
    haystack = " ".join(
        (
            record.capability_id,
            record.original_weakness,
            record.successful_mechanism,
            record.local_repair_contribution,
            record.regression_evidence,
        )
    )
    return criterion in haystack


def satisfied_main_goal_criteria(main_goal: MainGoalContract, knowledge_ledger: Sequence[CapabilityKnowledgeRecord]) -> tuple[str, ...]:
    satisfied: list[str] = []
    for criterion in main_goal.success_criteria:
        if any(capability_satisfies_criterion(record, criterion) for record in knowledge_ledger):
            satisfied.append(criterion)
    return tuple(satisfied)


def unmet_main_goal_criteria(main_goal: MainGoalContract, knowledge_ledger: Sequence[CapabilityKnowledgeRecord]) -> tuple[str, ...]:
    satisfied = set(satisfied_main_goal_criteria(main_goal, knowledge_ledger))
    return tuple(item for item in main_goal.success_criteria if item not in satisfied)


def derive_subgoal_evidence_for_main_goal(
    main_goal: MainGoalContract,
    knowledge_ledger: Sequence[CapabilityKnowledgeRecord],
    *,
    max_items: int = 1,
) -> tuple[dict[str, Any], ...]:
    evidence: list[dict[str, Any]] = []
    satisfied = set(satisfied_main_goal_criteria(main_goal, knowledge_ledger))
    inventory = capability_inventory_from_knowledge(knowledge_ledger)
    verified_categories = {item.category for item in inventory if item.status in {"functional", "reliable", "transferable"}}
    verified_capabilities = {item.capability_id for item in inventory if item.status in {"functional", "reliable", "transferable"}}
    for criterion in unmet_main_goal_criteria(main_goal, knowledge_ledger):
        prerequisites = tuple(main_goal.prerequisite_graph.get(criterion) or ())
        if prerequisites and not all(item in satisfied or item in verified_categories or item in verified_capabilities for item in prerequisites):
            continue
        evidence.append(
            {
                "evidence_source": f"main_goal:{main_goal.main_goal_id}:unmet:{criterion}",
                "observed_behavior": f"{criterion} remains required for {main_goal.normalized_objective}",
                "first_incorrect_transition": f"{main_goal.normalized_objective} -> unmet prerequisite {criterion} -> subgoal required",
                "affected_capability": criterion,
                "baseline_metric": f"{criterion}=0.0",
                "confidence": 0.86,
                "operator_value": 0.9,
                "severity": 0.78,
                "estimated_implementation_breadth": "small",
                "validation_method": "hierarchical_main_goal_assessment",
                "scope": "local_runtime",
                "uncertainty": "derived from main-goal success criteria and capability inventory",
            }
        )
        if len(evidence) >= max_items:
            break
    return tuple(evidence)


def assess_main_goal_completion(
    main_goal: MainGoalContract,
    knowledge_ledger: Sequence[CapabilityKnowledgeRecord],
    *,
    eligible_frontier_exists: bool,
) -> MainGoalContract:
    completed_subgoals = tuple(main_goal.completed_subgoals)
    capability_changes = tuple(main_goal.capability_changes)
    newly_discovered = tuple(main_goal.newly_discovered_prerequisites)
    satisfied = satisfied_main_goal_criteria(main_goal, knowledge_ledger)
    missing = tuple(item for item in main_goal.success_criteria if item not in set(satisfied))
    if not missing:
        return MainGoalContract(
            **{
                **main_goal.as_dict(),
                "completed_subgoals": tuple(dict.fromkeys(completed_subgoals + satisfied)),
                "capability_changes": tuple(dict.fromkeys(capability_changes + satisfied)),
                "disposition": "satisfied",
                "residual_uncertainty": "success criteria satisfied by capability knowledge ledger",
                "completion_rationale": "all required criteria have satisfied evidence",
            }
        )
    if eligible_frontier_exists:
        return MainGoalContract(
            **{
                **main_goal.as_dict(),
                "completed_subgoals": tuple(dict.fromkeys(completed_subgoals + satisfied)),
                "capability_changes": tuple(dict.fromkeys(capability_changes + satisfied)),
                "disposition": "active",
                "residual_uncertainty": f"remaining criteria: {', '.join(missing)}",
                "completion_rationale": "eligible subgoals remain",
            }
        )
    return MainGoalContract(
        **{
            **main_goal.as_dict(),
            "completed_subgoals": tuple(dict.fromkeys(completed_subgoals + satisfied)),
            "capability_changes": tuple(dict.fromkeys(capability_changes + satisfied)),
            "newly_discovered_prerequisites": tuple(dict.fromkeys(newly_discovered + missing)),
            "disposition": "partially_satisfied",
            "residual_uncertainty": f"frontier empty but required criteria remain: {', '.join(missing)}",
            "completion_rationale": "empty frontier is not completion; remaining criteria must produce new subgoals or a block",
        }
    )


def derive_next_main_goal(contract: BroadMissionContract, completed_goal: MainGoalContract, knowledge_ledger: Sequence[CapabilityKnowledgeRecord]) -> MainGoalContract | None:
    gained = tuple(dict.fromkeys(record.capability_id for record in knowledge_ledger if record.reassessment == "satisfied"))
    if completed_goal.normalized_objective == "developmental_self_assessment":
        objective = compile_long_horizon_objective(contract.original_operator_goal)
        plan = derive_developmental_capability_plan(objective, capability_inventory_from_knowledge(knowledge_ledger))
        return main_goal_from_developmental_plan(contract, plan)
    if completed_goal.normalized_objective == "real_continuous_mission_execution":
        objective = "Improve autonomous evidence discovery and weakness formulation"
        normalized = "autonomous_evidence_discovery"
        criteria = (
            "evidence_discovery_from_failed_attempts",
            "new_prerequisite_insertion",
            "semantic_replay_prevention",
        )
    else:
        return None
    return MainGoalContract(
        main_goal_id=stable_id("continuous-main-goal", contract.mission_id, normalized, gained),
        parent_mission_id=contract.mission_id,
        original_objective=objective,
        normalized_objective=normalized,
        success_criteria=criteria,
        evidence_requirements=("capability_inventory", "unresolved_gap_evidence", "measurable_subgoal"),
        prerequisite_graph={item: () for item in criteria},
        known_subgoals=(),
        active_subgoal="",
        completed_subgoals=(),
        blocked_subgoals=(),
        rejected_strategies=(),
        newly_discovered_prerequisites=(),
        residual_uncertainty="new main goal derived from completed goal and capability inventory",
        capability_changes=gained,
        disposition="active",
        completion_rationale=f"derived after {completed_goal.main_goal_id} disposition {completed_goal.disposition}",
        next_main_goal_candidates=(),
    )


def _normalize_development_objective(objective: str) -> str:
    lowered = objective.lower()
    if "science" in lowered or "physics" in lowered:
        return "master_sciences"
    if "research" in lowered:
        return "scientific_research_capability"
    if "learn" in lowered or "master" in lowered or "capable" in lowered or "develop" in lowered:
        return "general_developmental_capability"
    return "general_developmental_capability"


def _is_developmental_direction(objective: str) -> bool:
    lowered = objective.lower()
    if lowered.strip().rstrip(".") == "optimize your runtime":
        return False
    return any(term in lowered for term in ("capable", "master", "learn", "science", "research", "develop", "understand"))


def _objective_requirement_model(objective: LongHorizonObjective) -> Mapping[str, tuple[str, ...]]:
    lowered = objective.original_objective.lower()
    requirements: dict[str, tuple[str, ...]] = {
        "capability_inventory_generation": (),
        "developmental_gap_analysis": ("capability_inventory_generation",),
        "operator_progress_explanation": ("capability_inventory_generation",),
    }
    if any(term in lowered for term in ("science", "scientific", "physics", "math", "mathematics", "research")):
        requirements.update(
            {
                "sandbox_execution": (),
                "symbolic_math_environment": ("sandbox_execution",),
                "numerical_experiment_environment": ("sandbox_execution",),
                "unit_aware_quantity_system": ("symbolic_math_environment",),
                "derivation_validation": ("symbolic_math_environment",),
                "exercise_generation_and_grading": ("sandbox_execution",),
                "scientific_evidence_governance": ("governed_evidence_handling",),
            }
        )
    return requirements


def _derived_gap_for_objective(objective: LongHorizonObjective, missing: Sequence[str]) -> str:
    if not missing:
        return "prerequisite_capabilities_ready_for_next_curriculum_step"
    if any(item in set(missing) for item in ("symbolic_math_environment", "numerical_experiment_environment", "scientific_evidence_governance")):
        return "no_validated_scientific_learning_environment"
    return "developmental_self_direction_prerequisites_missing"


def _next_goal_for_gap(objective: LongHorizonObjective, missing: Sequence[str]) -> tuple[str, str]:
    missing_set = set(missing)
    if not missing:
        return ("Begin the next structured learning or research step with held-out validation", "validated_learning_step")
    if missing_set.intersection({"symbolic_math_environment", "numerical_experiment_environment", "scientific_evidence_governance"}):
        return ("Build and validate a governed mathematics and science sandbox", "governed_math_science_sandbox")
    return ("Build and validate developmental self-direction evidence", "developmental_self_direction_evidence")


def assess_developmental_capability_state(
    objective: LongHorizonObjective,
    inventory: Sequence[VerifiedCapability],
) -> DevelopmentalSelfAssessment:
    verified = tuple(item.capability_id for item in inventory if item.status in {"functional", "reliable", "transferable"})
    assumed = tuple(item.capability_id for item in inventory if item.status not in {"functional", "reliable", "transferable"})
    categories = {item.category for item in inventory if item.status in {"functional", "reliable", "transferable"}}
    requirements = _objective_requirement_model(objective)
    missing = tuple(item for item in requirements if item not in categories and item not in verified)
    enabled: list[str] = []
    if "sandbox_execution" in categories or any("sandbox" in item for item in verified):
        enabled.append("isolated local candidate experimentation")
    if "governed_evidence_handling" in categories or any("evidence" in item for item in verified):
        enabled.append("evidence-backed prerequisite comparison")
    if "operator_boundary_handling" in categories or any("operator" in item for item in verified):
        enabled.append("operator-gated application decisions")
    if not enabled and verified:
        enabled.append("limited developmental reassessment from retained capability evidence")
    questions = _confidence_questions_for_objective(objective, missing)
    resources = _recommended_resources_for_objective(objective, missing)
    confidence = 0.78 if verified and missing else 0.62 if missing else 0.88
    return DevelopmentalSelfAssessment(
        assessment_id=stable_id("developmental-self-assessment", objective.objective_id, verified, assumed, missing),
        objective_id=objective.objective_id,
        verified_capabilities=verified,
        assumed_capabilities=assumed,
        newly_enabled_possibilities=tuple(enabled),
        unsupported_claims=(
            "domain mastery",
            "general scientific reasoning",
            "validated prerequisite graph completeness",
        )
        if missing
        else ("domain mastery from one validation pass",),
        developmental_gaps=missing,
        missing_confidence_questions=questions,
        recommended_resources=resources,
        confidence=confidence,
        needs_additional_insight=confidence < 0.8 or bool(questions),
    )


def _confidence_questions_for_objective(objective: LongHorizonObjective, missing: Sequence[str]) -> tuple[str, ...]:
    if not missing:
        return ()
    lowered = objective.original_objective.lower()
    questions = ["Which missing prerequisite most blocks the next measurable developmental step?"]
    if any(term in lowered for term in ("science", "scientific", "physics", "math", "mathematics")):
        questions.extend(
            (
                "Which symbolic and numerical operations are required before the first science learning cycle?",
                "Which validation cases would show transfer rather than memorized examples?",
                "Which local libraries are available for safe mathematical experimentation?",
            )
        )
    return tuple(questions)


def _recommended_resources_for_objective(objective: LongHorizonObjective, missing: Sequence[str]) -> tuple[str, ...]:
    resources = ["retained capability evidence", "prior failed attempts", "repository inspection"]
    lowered = objective.original_objective.lower()
    if missing:
        resources.append("local deterministic experiments")
    if any(term in lowered for term in ("science", "scientific", "physics", "math", "mathematics")):
        resources.extend(
            (
                "local Python library inspection for SymPy/NumPy/SciPy availability",
                "governed reference or wiki lookup when local evidence is insufficient",
            )
        )
    resources.append("local model or provider critique only as advisory synthesis when separately authorized")
    return tuple(dict.fromkeys(resources))


def compile_developmental_insight_requests(assessment: DevelopmentalSelfAssessment) -> tuple[DevelopmentalInsightRequest, ...]:
    if not assessment.needs_additional_insight:
        return ()
    requests: list[DevelopmentalInsightRequest] = []
    for index, question in enumerate(assessment.missing_confidence_questions[:3], start=1):
        resource = assessment.recommended_resources[min(index - 1, len(assessment.recommended_resources) - 1)] if assessment.recommended_resources else "retained capability evidence"
        requests.append(
            DevelopmentalInsightRequest(
                request_id=stable_id("developmental-insight-request", assessment.assessment_id, question, resource),
                objective_id=assessment.objective_id,
                question=question,
                confidence_reason="current verified capability evidence does not fully determine the next prerequisite",
                selected_resource=resource,
                expected_evidence="evidence that changes the prerequisite ranking or confirms a safe next-goal boundary",
                authority_boundary="resource output is evidence only and cannot authorize mutation, API expansion, Git, or deployment",
            )
        )
    return tuple(requests)


def compile_developmental_operator_explanation(
    objective: LongHorizonObjective,
    assessment: DevelopmentalSelfAssessment,
    plan: DevelopmentalCapabilityPlan,
) -> DevelopmentalOperatorExplanation:
    verified_text = ", ".join(assessment.verified_capabilities) if assessment.verified_capabilities else "no fully verified capabilities in the supplied ledger"
    gap_text = ", ".join(assessment.developmental_gaps) if assessment.developmental_gaps else "no immediate prerequisite gap from the current model"
    return DevelopmentalOperatorExplanation(
        explanation_id=stable_id("developmental-operator-explanation", objective.objective_id, assessment.assessment_id, plan.plan_id),
        objective_id=objective.objective_id,
        current_understanding=f"I can only claim abilities backed by retained evidence. Current verified evidence: {verified_text}.",
        verified_abilities=assessment.verified_capabilities,
        assumed_or_unverified_abilities=assessment.assumed_capabilities + assessment.unsupported_claims,
        missing_prerequisites=assessment.developmental_gaps,
        next_goal=plan.next_main_goal,
        why_next_goal_matters=f"This goal addresses {plan.derived_gap} before attempting broader claims about {objective.original_objective}.",
        uncertainty=f"Confidence {assessment.confidence:.2f}; unresolved questions: {gap_text}.",
        authority_boundary=plan.authority_boundary,
    )


def _capability_category(*parts: str) -> str:
    text = " ".join(parts).lower()
    if "sandbox" in text or "execution" in text:
        return "sandbox_execution"
    if "evidence" in text or "provenance" in text:
        return "governed_evidence_handling"
    if "model" in text or "reference" in text:
        return "resource_selection"
    if "operator" in text or "application" in text:
        return "operator_boundary_handling"
    if "math" in text or "symbolic" in text:
        return "symbolic_math_environment"
    return "runtime_governance"


def evidence_to_findings(evidence_records: Sequence[Mapping[str, Any]]) -> tuple[RuntimeFinding, ...]:
    findings: list[RuntimeFinding] = []
    for record in evidence_records:
        if not record.get("evidence_source") or not record.get("observed_behavior"):
            continue
        diagnostic_only = bool(record["diagnostic_only"]) if "diagnostic_only" in record else not bool(record.get("baseline_metric") or record.get("reproducible_failure"))
        findings.append(
            RuntimeFinding(
                finding_id=str(record.get("finding_id") or stable_id("runtime-finding", record.get("evidence_source"), record.get("observed_behavior"))),
                evidence_source=str(record["evidence_source"]),
                observed_behavior=str(record["observed_behavior"]),
                first_incorrect_transition=str(record.get("first_incorrect_transition") or "diagnostic_transition_not_yet_localized"),
                affected_capability=str(record.get("affected_capability") or "unknown"),
                baseline_metric=str(record.get("baseline_metric") or record.get("reproducible_failure") or "diagnostic_only"),
                confidence=float(record.get("confidence") or 0.5),
                uncertainty=str(record.get("uncertainty") or "bounded to supplied evidence"),
                scope=str(record.get("scope") or "local_runtime"),
                operator_value=float(record.get("operator_value") or 0.5),
                severity=float(record.get("severity") or 0.5),
                estimated_implementation_breadth=str(record.get("estimated_implementation_breadth") or "small"),
                validation_method=str(record.get("validation_method") or "focused_test"),
                diagnostic_only=diagnostic_only,
            )
        )
    return tuple(findings)


def weakness_from_finding(finding: RuntimeFinding) -> WeaknessCandidate | None:
    if finding.diagnostic_only:
        return None
    semantic_signature = stable_id(
        "continuous-weakness",
        finding.affected_capability,
        finding.first_incorrect_transition,
        finding.baseline_metric,
        finding.validation_method,
    )
    priority = round((finding.severity * 0.45) + (finding.operator_value * 0.35) + (finding.confidence * 0.20), 6)
    return WeaknessCandidate(
        weakness_id=stable_id("weakness", semantic_signature),
        semantic_signature=semantic_signature,
        description=finding.observed_behavior,
        first_incorrect_transition=finding.first_incorrect_transition,
        source_evidence=(finding.evidence_source,),
        measurable_target=f"{finding.affected_capability} improves beyond {finding.baseline_metric}",
        baseline=finding.baseline_metric,
        controls=("existing_satisfied_capabilities_remain_stable",),
        adversarial_plan=f"challenge {finding.affected_capability} with quote, contradiction, and control variants",
        held_out_plan="use held-out policy label from evidence; do not upgrade disclosed cases to sealed",
        prerequisites=(),
        estimated_scope=finding.estimated_implementation_breadth,
        risk=round(1.0 - finding.confidence, 6),
        operator_value=finding.operator_value,
        priority=priority,
    )


def rank_weakness_frontier(
    findings: Sequence[RuntimeFinding],
    *,
    consumed_signatures: Sequence[str] = (),
    knowledge_ledger: Sequence[CapabilityKnowledgeRecord] = (),
) -> tuple[WeaknessCandidate, ...]:
    consumed = set(consumed_signatures)
    solved = {record.capability_id for record in knowledge_ledger if record.reassessment == "satisfied"}
    frontier: list[WeaknessCandidate] = []
    for finding in findings:
        candidate = weakness_from_finding(finding)
        if candidate is None:
            continue
        if candidate.semantic_signature in consumed:
            candidate = WeaknessCandidate(**{**candidate.as_dict(), "status": "superseded"})
        if finding.affected_capability in solved:
            candidate = WeaknessCandidate(**{**candidate.as_dict(), "status": "satisfied"})
        frontier.append(candidate)
    return tuple(sorted(frontier, key=lambda item: (-item.priority, item.weakness_id)))


def compile_active_subgoal(contract: BroadMissionContract, frontier: Sequence[WeaknessCandidate]) -> ActiveSubgoal | None:
    eligible = [item for item in frontier if item.status == "eligible"]
    if not eligible:
        return None
    selected = eligible[0]
    return ActiveSubgoal(
        subgoal_id=stable_id("subgoal", contract.mission_id, selected.semantic_signature),
        source_mission_id=contract.mission_id,
        weakness_id=selected.weakness_id,
        measurable_objective=selected.measurable_target,
        baseline=selected.baseline,
        success_threshold="target_metric_improves_and_controls_do_not_regress",
        controls=selected.controls,
        adversarial_tests=selected.adversarial_plan,
        held_out_policy=selected.held_out_plan,
        sandbox_scope="local_sandbox_only_until_operator_application",
        source_inspection_scope=("orchestration/runtime", "tests/runtime_gsr"),
        tracked_application_allowlist=("orchestration/runtime", "tests/runtime_gsr"),
        rollback_condition="rollback exact application if tracked validation differs from sandbox reproduction",
    )


def consumed_signatures_after_reassessment(
    frontier: Sequence[WeaknessCandidate],
    active_subgoal: Mapping[str, Any] | None,
    consumed_signatures: Sequence[str],
) -> tuple[str, ...]:
    consumed = list(consumed_signatures)
    if not active_subgoal:
        return tuple(consumed)
    weakness_id = str(active_subgoal.get("weakness_id") or "")
    selected = next((item for item in frontier if item.weakness_id == weakness_id), None)
    if selected and selected.semantic_signature not in consumed:
        consumed.append(selected.semantic_signature)
    return tuple(consumed)


def api_unavailable_update(api: ApiAuthorityState, *, pending_task: str, reason: str) -> ApiAuthorityState:
    return ApiAuthorityState(
        enabled=False,
        allowed_providers=api.allowed_providers,
        allowed_models=api.allowed_models,
        call_allowance=api.call_allowance,
        token_allowance=api.token_allowance,
        cost_allowance=api.cost_allowance,
        calls_consumed=api.calls_consumed,
        tokens_consumed=api.tokens_consumed,
        reported_cost=api.reported_cost,
        failures=api.failures,
        retries=api.retries,
        pending_provider_tasks=tuple(dict.fromkeys(api.pending_provider_tasks + (pending_task,))),
        last_provider_result=api.last_provider_result,
        unavailability_reason=reason,
    )


def dirty_worktree_policy(paths: Sequence[str]) -> dict[str, Any]:
    protected_touched = [path for path in paths if path == "DELTA-75" or path.startswith("DELTA-75/")]
    rc4_noise = [path for path in paths if path.startswith("reports/RC4_")]
    unrelated = [path for path in paths if path not in rc4_noise and path not in protected_touched]
    return {
        "protected_paths_touched": tuple(protected_touched),
        "rc4_refresh_noise": tuple(rc4_noise),
        "unrelated_dirty_paths": tuple(unrelated),
        "safe_to_stage_broadly": False,
        "reports_rc4_excluded": True,
        "delta75_prohibited": True,
    }


def make_satisfied_transfer_record() -> CapabilityKnowledgeRecord:
    return CapabilityKnowledgeRecord(
        capability_id="transfer_dependency_identity_preservation",
        original_weakness="dependency identity dropped before transfer validation",
        evidence=("LIVE45 transfer application_result.json",),
        first_incorrect_transition="dependency citation text -> dependency identity not preserved before classification",
        strategies_attempted=("provider candidate", "sandbox repair", "clean reproduction", "tracked application"),
        failed_approaches=("unvalidated provider-only candidate",),
        successful_mechanism="preserve dependency id in structured record before classification",
        exact_candidate="orchestration/runtime/live45_transfer_dependency_candidate.py",
        tests_added=("tests/runtime_gsr/test_live45_transfer_dependency_candidate.py",),
        metrics_before_after={"target": (0.0, 1.0), "held_out": (0.0, 1.0)},
        controls=("quote_instruction_control",),
        adversarial_evidence=("instruction-like dependency text ignored",),
        held_out_evidence={"sealed": True, "result": 1.0},
        reproduction_evidence="declared-input reproduction passed",
        provider_contribution="initial candidate generation",
        local_repair_contribution="path hardening and strict reproduction",
        application_evidence="operator-approved tracked application",
        regression_evidence="bounded adjacency passed",
        reassessment="satisfied",
        residual_uncertainty="limited to current dependency id grammar",
        reusable_process_rules=("sandbox success requires clean reproduction", "path hardening must avoid manual PYTHONPATH"),
    )
