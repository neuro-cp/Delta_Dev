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

CAPABILITY_EVIDENCE_STAGES = (
    "hypothesis",
    "candidate_structurally_validated",
    "evaluation_pending",
    "behaviorally_demonstrated",
    "behaviorally_failed",
    "operator_accepted",
    "operator_rejected",
)
CAPABILITY_ACQUIRED_STAGES = {"behaviorally_demonstrated", "operator_accepted"}
STRUCTURAL_ONLY_STAGES = {"hypothesis", "candidate_structurally_validated", "evaluation_pending"}
BEHAVIORAL_EVALUATION_DISPOSITIONS = (
    "evaluation_pending",
    "behaviorally_demonstrated",
    "behaviorally_failed",
    "insufficient_independent_evidence",
    "invalid_evaluation",
    "blocked_by_authority",
    "blocked_by_resource",
)
BEHAVIORAL_FAILURE_SOURCE_TYPES = (
    "failing_test",
    "runtime_transition_violation",
    "retained_behavioral_evaluation_failure",
    "restart_regression",
    "user_visible_reproduction",
    "benchmark_failure",
    "durable_runtime_failure",
    "runtime_exception",
    "operator_report",
    "model_advisory",
    "activity_artifact",
)
STRONG_BEHAVIORAL_FAILURE_SOURCES = {
    "failing_test",
    "runtime_transition_violation",
    "retained_behavioral_evaluation_failure",
    "restart_regression",
    "benchmark_failure",
}
REPRODUCIBILITY_STATUSES = (
    "reproduced",
    "intermittently_reproduced",
    "not_reproduced",
    "reproduction_pending",
    "reproduction_unsafe",
    "requires_corroboration",
)
AUTHORITY_CLASSES = (
    "local_execution_allowed",
    "operator_authority_required",
    "protected_scope",
    "resource_blocked",
    "accepted_boundary",
    "unknown_authority",
)
AMBIGUITY_STATUSES = (
    "resolved",
    "bounded_uncertainty",
    "unresolved_material_ambiguity",
    "missing_expected_behavior",
    "missing_owner_scope",
    "conflicting_evidence",
)
TASK_ELIGIBILITY_STATUSES = (
    "eligible",
    "ineligible_activity_only",
    "ineligible_structural_only",
    "ineligible_unreproduced",
    "ineligible_missing_expectation",
    "ineligible_missing_transition",
    "ineligible_accepted_boundary",
    "ineligible_duplicate",
    "blocked_authority",
    "blocked_resource",
    "unresolved_ambiguity",
)
BEHAVIORAL_FAILURE_DISPOSITIONS = (
    "observed",
    "normalized",
    "reproduction_pending",
    "reproducible_material_failure",
    "intermittent_material_failure",
    "insufficient_evidence",
    "task_eligible",
    "task_compiled",
    "candidate_pending",
    "behaviorally_demonstrated",
    "behaviorally_failed",
    "accepted_boundary",
    "closed_repaired",
    "closed_invalid",
    "closed_duplicate",
)
REPOSITORY_BEHAVIOR_CONTRACT_DISPOSITIONS = (
    "locally_implementable_by_existing_pcm",
    "locally_implementable_but_pcm_operation_unsupported",
    "missing_repository_evidence",
    "missing_independent_behavior_contract",
    "unresolved_failure_mechanism",
    "blocked_by_authority",
    "blocked_by_resource",
    "accepted_boundary",
    "invalid_scope",
)
EXPECTED_BEHAVIOR_AUTHORITIES = (
    "preexisting_test_assertion",
    "state_machine_transition_contract",
    "sealed_benchmark_predicate",
    "sealed_behavioral_evaluation_bundle",
    "durable_protocol_invariant",
    "operator_approved_replay_contract",
    "concrete_mission_success_criterion",
)
FORBIDDEN_BEHAVIORAL_FAILURE_KEYS = {
    "patch",
    "patch_text",
    "replacement_text",
    "candidate_code",
    "candidate_source",
    "intended_patch",
    "intended_implementation",
    "implementation",
    "model_success_claim",
    "candidate_authored_success_criteria",
}


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
    execution_kind: str = "sandbox_development"
    behavioral_evaluation: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RepositoryBehaviorContract:
    contract_id: str
    failure_id: str
    semantic_failure_key: str
    mission_id: str
    main_goal_id: str
    subgoal_id: str
    weakness_id: str
    capability_id: str
    affected_path: str
    affected_symbol_or_transition: str
    inspected_path_digest: str
    source_inspection_id: str
    current_behavior: str
    expected_behavior: str
    expected_behavior_identity: str
    first_incorrect_transition: str
    failure_mechanism: str
    candidate_behavior: str
    expected_observable_change: str
    independent_evidence_path: str
    independent_evidence_digest: str
    independent_validation_predicate: str
    baseline_reproduction_reference: str
    control_requirements: tuple[str, ...]
    held_out_requirements: tuple[str, ...]
    restoration_condition: str
    allowed_paths: tuple[str, ...]
    excluded_paths: tuple[str, ...]
    local_implementation_eligibility: str
    authority_class: str
    ambiguity_status: str
    failure_evidence_digest: str
    contract_protocol: str
    contract_version: str
    contract_digest: str
    advisory_model_digest: str = ""
    missing_fields: tuple[str, ...] = ()
    validation_errors: tuple[str, ...] = ()
    version_of: str = ""
    duplicate_of: str = ""

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
    evidence_stage: str = "legacy_unclassified"
    capability_acquired: bool = False
    eligible_for_behavioral_evaluation: bool = False
    behavioral_evaluation_ref: str = ""
    behavioral_evaluation: Mapping[str, Any] | None = None
    legacy_recovery_disposition: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BehavioralEvaluationRecord:
    evaluation_id: str
    task_family_id: str
    capability_id: str
    developmental_gap_id: str
    baseline_attempt_id: str
    candidate_id: str
    evaluation_protocol_version: str
    task_source: str
    training_case_ids: tuple[str, ...]
    sealed_or_preexisting_case_ids: tuple[str, ...]
    control_case_ids: tuple[str, ...]
    baseline_metrics: Mapping[str, Any]
    post_candidate_metrics: Mapping[str, Any]
    transfer_metrics: Mapping[str, Any]
    regression_metrics: Mapping[str, Any]
    evidence_independence: Mapping[str, Any]
    disposition: str
    evidence_refs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReproductionAttemptRecord:
    attempt_id: str
    command_or_predicate_identity: str
    input_or_state_reference: str
    started_at: str
    completed_at: str
    status: str
    result_classification: str
    stdout_digest: str = ""
    stderr_digest: str = ""
    result_digest: str = ""
    timeout_or_resource_result: str = ""
    environment_digest: str = ""
    safety_boundary: str = "local_deterministic_no_mutation"
    authoritative_runner_identity: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BehavioralFailureRecord:
    failure_id: str
    semantic_failure_key: str
    source_type: str
    source_reference: str
    source_digest: str
    observed_behavior: str
    expected_behavior: str
    expected_behavior_identity: str
    expected_vs_observed_result: str
    baseline_reproduction: str
    reproduction_command_or_predicate: str
    reproduction_attempts: tuple[dict[str, Any], ...]
    reproduction_result: str
    reproduction_output_digest: str
    first_incorrect_transition: str
    affected_runtime_stage: str
    affected_capability_id: str
    originating_mission_id: str
    suspected_owner_paths: tuple[str, ...]
    independent_evidence_paths: tuple[str, ...]
    allowed_scope: tuple[str, ...]
    excluded_scope: tuple[str, ...]
    materiality_reason: str
    reproducibility_status: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    environment_digest: str
    state_digest: str
    evidence_digest: str
    sealed_failure_bundle_digest: str
    authority_class: str
    ambiguity_status: str
    task_eligibility: str
    current_disposition: str
    duplicate_of: str = ""
    version_of: str = ""
    advisory_model_digest: str = ""
    closure_reason: str = ""
    closed_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BehavioralFailureCompilationResult:
    accepted: bool
    record: BehavioralFailureRecord | None
    rejection_reason: str
    missing_fields: tuple[str, ...]
    source_classification: str
    duplicate_of: str = ""
    version_of: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["record"] = self.record.as_dict() if self.record is not None else None
        return data


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


@dataclass(frozen=True)
class DevelopmentalNextGoalCandidate:
    candidate_id: str
    normalized_objective: str
    objective: str
    evidence_basis: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    confidence_before: float
    expected_value: float
    risk: float
    resource_need: str
    rationale: str
    success_criteria: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    prerequisite_graph: Mapping[str, tuple[str, ...]]

    @property
    def score(self) -> float:
        return round((self.confidence_before * 0.25) + (self.expected_value * 0.55) - (self.risk * 0.2), 4)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score"] = self.score
        return data


def _canonical_rationale_text(rationale: str) -> str:
    text = str(rationale or "").strip()
    marker = "selected from ranked developmental next-goal candidates"
    if marker in text:
        return marker + text.rsplit(marker, 1)[1]
    if "; prior_active_rationale=" in text:
        text = text.split("; prior_active_rationale=", 1)[0]
    if "; prior_rationale_summary=" in text:
        text = text.split("; prior_rationale_summary=", 1)[0]
    return text


def _completion_rationale_with_reference(event: str, main_goal: MainGoalContract) -> str:
    if not main_goal.next_main_goal_candidates or not main_goal.completion_rationale:
        return event
    canonical = _canonical_rationale_text(main_goal.completion_rationale)
    rationale_id = stable_id("main-goal-rationale", main_goal.main_goal_id, canonical)
    return f"{event}; prior_rationale_id={rationale_id}; prior_rationale_summary={canonical}"


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
    for raw_record in knowledge_ledger:
        record = normalize_capability_record_for_recovery(raw_record)
        stage = capability_evidence_stage(record)
        if capability_is_acquired(record):
            status = "functional"
        elif stage in STRUCTURAL_ONLY_STAGES:
            status = "structurally_valid_candidate"
        elif stage == "behaviorally_failed":
            status = "behaviorally_failed"
        else:
            status = "emerging" if record.reassessment else "unverified"
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


def _limitation_gap_evidence(inventory: Sequence[VerifiedCapability]) -> tuple[Mapping[str, Any], ...]:
    gap_records: dict[str, dict[str, Any]] = {}

    def add_gap(gap_id: str, capability: VerifiedCapability, reason: str, question: str, resource: str, materiality: float) -> None:
        record = gap_records.setdefault(
            gap_id,
            {
                "gap_id": gap_id,
                "capabilities": [],
                "reasons": [],
                "confidence_question": question,
                "recommended_resource": resource,
                "materiality": materiality,
            },
        )
        if capability.capability_id not in record["capabilities"]:
            record["capabilities"].append(capability.capability_id)
        if reason not in record["reasons"]:
            record["reasons"].append(reason)
        record["materiality"] = max(float(record["materiality"]), materiality)

    for item in inventory:
        limitation_text = " ".join(item.limitations).lower()
        evidence_text = " ".join(item.evidence).lower()
        transfer_text = " ".join(item.transfer_evidence).lower()
        if "local diagnostic" in limitation_text or "local sandbox" in limitation_text:
            add_gap(
                "local_diagnostic_only_validation",
                item,
                "capability evidence is explicitly limited to local diagnostic or sandbox validation",
                "Which local diagnostic capabilities need non-fixture or tracked-path evidence before broader claims?",
                "retained capability evidence and local replay artifacts",
                0.82,
            )
        if "application review" in limitation_text or "tracked-source" in limitation_text or "tracked source" in limitation_text:
            add_gap(
                "missing_tracked_application_proof",
                item,
                "capability remains outside the governed tracked-source application path",
                "Which validated capability should next prove the operator-gated application path without mutating protected scope?",
                "application-boundary records and rollback evidence",
                0.9,
            )
        if "focused continuous subgoal executor tests" in evidence_text or "fixture" in limitation_text:
            add_gap(
                "fixture_scoped_validation",
                item,
                "validation evidence is focused and may not represent broader behavior",
                "Which capability needs a non-fixture or cross-context evaluation before it can be trusted more broadly?",
                "focused, held-out, adversarial, and transfer result comparison",
                0.74,
            )
        if not item.transfer_evidence or transfer_text in {"", "false", "none"}:
            add_gap(
                "missing_transfer_evidence",
                item,
                "capability lacks positive transfer evidence",
                "What transfer case would distinguish a reusable capability from a local pass?",
                "held-out and transfer artifact mining",
                0.78,
            )
        if "provider" in limitation_text or "provider" in evidence_text:
            add_gap(
                "provider_dependency_without_local_fallback",
                item,
                "capability evidence includes provider dependence without a local fallback proof",
                "Can the same developmental decision be supported by local evidence when provider access is unavailable?",
                "local replay and provider-free comparison",
                0.58,
            )

    return tuple(sorted(gap_records.values(), key=lambda record: (-float(record["materiality"]), str(record["gap_id"]))))


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


def capability_evidence_stage(record: CapabilityKnowledgeRecord | Mapping[str, Any]) -> str:
    raw = record.evidence_stage if isinstance(record, CapabilityKnowledgeRecord) else str(record.get("evidence_stage") or "")
    if raw in CAPABILITY_EVIDENCE_STAGES:
        return raw
    reassessment = record.reassessment if isinstance(record, CapabilityKnowledgeRecord) else str(record.get("reassessment") or "")
    evaluation_ref = record.behavioral_evaluation_ref if isinstance(record, CapabilityKnowledgeRecord) else str(record.get("behavioral_evaluation_ref") or "")
    acquired = record.capability_acquired if isinstance(record, CapabilityKnowledgeRecord) else bool(record.get("capability_acquired"))
    if acquired and evaluation_ref:
        return "behaviorally_demonstrated"
    if reassessment == "candidate_structurally_validated":
        return "candidate_structurally_validated"
    if reassessment == "evaluation_pending":
        return "evaluation_pending"
    if reassessment == "behaviorally_failed":
        return "behaviorally_failed"
    if reassessment == "satisfied" and not evaluation_ref:
        return "candidate_structurally_validated"
    return "hypothesis"


def capability_is_acquired(record: CapabilityKnowledgeRecord | Mapping[str, Any]) -> bool:
    stage = capability_evidence_stage(record)
    if stage not in CAPABILITY_ACQUIRED_STAGES:
        return False
    evaluation_ref = record.behavioral_evaluation_ref if isinstance(record, CapabilityKnowledgeRecord) else str(record.get("behavioral_evaluation_ref") or "")
    return bool(evaluation_ref)


def normalize_capability_record_for_recovery(record: CapabilityKnowledgeRecord) -> CapabilityKnowledgeRecord:
    stage = capability_evidence_stage(record)
    if record.reassessment == "satisfied" and stage == "candidate_structurally_validated" and not record.behavioral_evaluation_ref:
        return CapabilityKnowledgeRecord(
            **{
                **record.as_dict(),
                "reassessment": "candidate_structurally_validated",
                "evidence_stage": "candidate_structurally_validated",
                "capability_acquired": False,
                "eligible_for_behavioral_evaluation": True,
                "legacy_recovery_disposition": "legacy_satisfied_without_independent_behavioral_evaluation_downgraded",
                "residual_uncertainty": (
                    record.residual_uncertainty
                    + "; legacy satisfied record lacks independent behavioral evaluation and cannot promote capability"
                ),
            }
        )
    return CapabilityKnowledgeRecord(
        **{
            **record.as_dict(),
            "evidence_stage": stage,
            "capability_acquired": capability_is_acquired(record),
        }
    )


def validate_behavioral_evaluation(evaluation: BehavioralEvaluationRecord) -> tuple[bool, tuple[str, ...]]:
    failures: list[str] = []
    if evaluation.disposition not in BEHAVIORAL_EVALUATION_DISPOSITIONS:
        failures.append("unsupported_disposition")
    if not evaluation.sealed_or_preexisting_case_ids:
        failures.append("missing_sealed_or_preexisting_cases")
    if set(evaluation.training_case_ids) & set(evaluation.sealed_or_preexisting_case_ids):
        failures.append("training_cases_overlap_evaluation_cases")
    independence = dict(evaluation.evidence_independence or {})
    if independence.get("candidate_generated_expected_outputs") is True:
        failures.append("candidate_generated_expected_outputs")
    if independence.get("self_reported_success") is True:
        failures.append("self_reported_success")
    if independence.get("artifact_existence_only") is True:
        failures.append("artifact_existence_only")
    if independence.get("case_source") not in {"preexisting", "sealed", "independently_generated", "operator_supplied", "immutable_benchmark"}:
        failures.append("case_source_not_independent")
    baseline = float(evaluation.baseline_metrics.get("target", 0.0) or 0.0)
    post = float(evaluation.post_candidate_metrics.get("target", 0.0) or 0.0)
    transfer = float(evaluation.transfer_metrics.get("target", 0.0) or 0.0)
    controls = bool(evaluation.regression_metrics.get("controls_stable"))
    if evaluation.disposition == "behaviorally_demonstrated":
        if post <= baseline:
            failures.append("target_behavior_not_improved")
        if transfer < float(evaluation.transfer_metrics.get("threshold", 1.0) or 1.0):
            failures.append("transfer_threshold_not_met")
        if not controls:
            failures.append("controls_not_stable")
    return (not failures, tuple(failures))


def promote_capability_with_behavioral_evaluation(
    record: CapabilityKnowledgeRecord,
    evaluation: BehavioralEvaluationRecord,
    *,
    operator_accepted: bool = False,
) -> CapabilityKnowledgeRecord:
    valid, failures = validate_behavioral_evaluation(evaluation)
    if not valid or evaluation.disposition != "behaviorally_demonstrated":
        return CapabilityKnowledgeRecord(
            **{
                **record.as_dict(),
                "reassessment": "behaviorally_failed" if evaluation.disposition == "behaviorally_failed" else "insufficient_independent_evidence",
                "evidence_stage": "behaviorally_failed" if evaluation.disposition == "behaviorally_failed" else "evaluation_pending",
                "capability_acquired": False,
                "eligible_for_behavioral_evaluation": evaluation.disposition in {"evaluation_pending", "insufficient_independent_evidence"},
                "behavioral_evaluation_ref": evaluation.evaluation_id,
                "behavioral_evaluation": evaluation.as_dict(),
                "failed_approaches": tuple(dict.fromkeys(tuple(record.failed_approaches) + failures)),
            }
        )
    stage = "operator_accepted" if operator_accepted else "behaviorally_demonstrated"
    return CapabilityKnowledgeRecord(
        **{
            **record.as_dict(),
            "reassessment": stage,
            "evidence_stage": stage,
            "capability_acquired": True,
            "eligible_for_behavioral_evaluation": False,
            "behavioral_evaluation_ref": evaluation.evaluation_id,
            "behavioral_evaluation": evaluation.as_dict(),
            "metrics_before_after": {
                **dict(record.metrics_before_after),
                "behavioral_baseline": dict(evaluation.baseline_metrics),
                "behavioral_post_candidate": dict(evaluation.post_candidate_metrics),
                "behavioral_transfer": dict(evaluation.transfer_metrics),
                "behavioral_regression": dict(evaluation.regression_metrics),
            },
            "held_out_evidence": {
                **dict(record.held_out_evidence),
                "independent_cases": evaluation.sealed_or_preexisting_case_ids,
                "transfer": dict(evaluation.transfer_metrics),
            },
        }
    )


def capability_satisfies_criterion(record: CapabilityKnowledgeRecord, criterion: str) -> bool:
    record = normalize_capability_record_for_recovery(record)
    if not capability_is_acquired(record):
        return False
    if _criterion_requires_substantive_evidence(criterion):
        substantive = dict(record.metrics_before_after.get("substantive_evidence") or {})
        if substantive.get("passed") is not True:
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


def _criterion_requires_substantive_evidence(criterion: str) -> bool:
    return criterion in {
        "knowledge_retrieval_index",
        "prior_failure_avoidance_check",
        "next_goal_evidence_reuse_record",
        "available_resource_inventory",
        "local_resource_selection_trace",
        "authority_boundary_resource_filter",
        "local_model_advisory_probe",
        "reference_retrieval_probe",
        "resource_evidence_integration",
    }


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
        completion_rationale = _completion_rationale_with_reference("all required criteria have satisfied evidence", main_goal)
        return MainGoalContract(
            **{
                **main_goal.as_dict(),
                "completed_subgoals": tuple(dict.fromkeys(completed_subgoals + satisfied)),
                "capability_changes": tuple(dict.fromkeys(capability_changes + satisfied)),
                "disposition": "satisfied",
                "residual_uncertainty": "success criteria satisfied by capability knowledge ledger",
                "completion_rationale": completion_rationale,
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
            "completion_rationale": _completion_rationale_with_reference(
                "empty frontier is not completion; remaining criteria must produce new subgoals or a block",
                main_goal,
            ),
        }
    )


def derive_developmental_next_goal_candidates(
    contract: BroadMissionContract,
    completed_goal: MainGoalContract,
    knowledge_ledger: Sequence[CapabilityKnowledgeRecord],
) -> tuple[DevelopmentalNextGoalCandidate, ...]:
    if not _is_developmental_direction(contract.original_operator_goal):
        return ()

    recovered_knowledge = tuple(normalize_capability_record_for_recovery(record) for record in knowledge_ledger)
    satisfied = {record.capability_id for record in recovered_knowledge if capability_is_acquired(record)}
    def _candidate_already_satisfied(normalized_objective: str, criteria: Sequence[str]) -> bool:
        return completed_goal.normalized_objective == normalized_objective or all(item in satisfied for item in criteria)

    evidence_basis = tuple(
        record.capability_id
        for record in recovered_knowledge
        if capability_is_acquired(record) and record.capability_id in completed_goal.success_criteria
    )
    candidates: list[DevelopmentalNextGoalCandidate] = []
    if completed_goal.normalized_objective == "meaningful_progress_stall_detection" and "frontier_uncertainty_scan" not in satisfied:
        candidates.append(
            DevelopmentalNextGoalCandidate(
                candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "autonomous_evidence_acquisition"),
                normalized_objective="autonomous_evidence_acquisition",
                objective="Develop autonomous evidence acquisition for the next unknown developmental frontier",
                evidence_basis=evidence_basis,
                missing_evidence=("frontier uncertainty record", "local artifact evidence", "candidate gap record"),
                confidence_before=0.35,
                expected_value=0.92,
                risk=0.18,
                resource_need="local_artifact_mining_first",
                rationale=(
                    "meaningful progress tracking is verified, but the capability inventory still lacks proof that an empty or stalled "
                    "frontier triggers new evidence acquisition before another developmental goal is selected"
                ),
                success_criteria=(
                    "frontier_uncertainty_scan",
                    "local_artifact_evidence_acquisition",
                    "next_gap_candidate_generation",
                ),
                evidence_requirements=("frontier_scan_record", "local_artifact_evidence", "candidate_gap_record"),
                prerequisite_graph={
                    "frontier_uncertainty_scan": (),
                    "local_artifact_evidence_acquisition": ("frontier_uncertainty_scan",),
                    "next_gap_candidate_generation": ("local_artifact_evidence_acquisition",),
                },
            )
        )
    if completed_goal.normalized_objective == "meaningful_progress_stall_detection" and "state_grounded_progress_summary" in satisfied and "operator_goal_reinterpretation_check" not in satisfied:
        candidates.append(
            DevelopmentalNextGoalCandidate(
                candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "operator_goal_reinterpretation_check"),
                normalized_objective="operator_goal_reinterpretation_check",
                objective="Develop a check that prevents broad operator goals from being reinterpreted after evidence changes",
                evidence_basis=evidence_basis,
                missing_evidence=("goal-drift comparison record", "operator-goal preservation evidence"),
                confidence_before=0.5,
                expected_value=0.62,
                risk=0.22,
                resource_need="controller_state_comparison",
                rationale="grounded communication exists, but broad-goal preservation is a lower-value risk than missing frontier evidence",
                success_criteria=("goal_drift_comparison", "operator_goal_preservation_record"),
                evidence_requirements=("original_goal_digest", "current_goal_digest", "drift_disposition"),
                prerequisite_graph={"goal_drift_comparison": (), "operator_goal_preservation_record": ("goal_drift_comparison",)},
            )
        )
    if completed_goal.normalized_objective == "meaningful_progress_stall_detection" and "stalled_execution_detection" in satisfied and "idle_resource_efficiency" not in satisfied:
        candidates.append(
            DevelopmentalNextGoalCandidate(
                candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "idle_resource_efficiency"),
                normalized_objective="idle_resource_efficiency",
                objective="Develop bounded idle-resource efficiency checks for observation mode",
                evidence_basis=evidence_basis,
                missing_evidence=("idle heartbeat sample", "bounded-resource comparison"),
                confidence_before=0.7,
                expected_value=0.45,
                risk=0.12,
                resource_need="runtime_status_sampling",
                rationale="idle efficiency is useful, but it does not decide what DELTA should learn next",
                success_criteria=("idle_heartbeat_truthfulness", "bounded_idle_resource_record"),
                evidence_requirements=("heartbeat_record", "resource_snapshot"),
                prerequisite_graph={"idle_heartbeat_truthfulness": (), "bounded_idle_resource_record": ("idle_heartbeat_truthfulness",)},
            )
        )
    if "next_gap_candidate_generation" in satisfied:
        transfer_criteria = (
            "cross_context_transfer_case_generation",
            "transfer_metric_validation",
            "transfer_regression_control",
        )
        if not _candidate_already_satisfied("capability_transfer_validation", transfer_criteria):
            candidates.append(
                DevelopmentalNextGoalCandidate(
                    candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "capability_transfer_validation"),
                    normalized_objective="capability_transfer_validation",
                    objective="Develop cross-context transfer validation for newly acquired developmental capabilities",
                    evidence_basis=evidence_basis,
                    missing_evidence=("cross-context transfer record", "domain-shift validation result", "transfer regression control"),
                    confidence_before=0.42,
                    expected_value=0.88,
                    risk=0.2,
                    resource_need="local_held_out_and_transfer_artifact_mining",
                    rationale=(
                        "autonomous evidence acquisition produced candidate gaps, but current capability claims are still mostly certified by narrow local "
                        "criteria; transfer validation is the highest-value next check before trusting broader self-directed development"
                    ),
                    success_criteria=transfer_criteria,
                    evidence_requirements=("transfer_case_record", "held_out_metric", "control_regression_record"),
                    prerequisite_graph={
                        "cross_context_transfer_case_generation": (),
                        "transfer_metric_validation": ("cross_context_transfer_case_generation",),
                        "transfer_regression_control": ("transfer_metric_validation",),
                    },
                )
            )
        source_criteria = ("source_diversity_inventory", "reference_evidence_comparison")
        if not _candidate_already_satisfied("evidence_source_diversity", source_criteria):
            candidates.append(
                DevelopmentalNextGoalCandidate(
                    candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "evidence_source_diversity"),
                    normalized_objective="evidence_source_diversity",
                    objective="Develop evidence-source diversity checks for developmental decisions",
                    evidence_basis=evidence_basis,
                    missing_evidence=("source diversity record", "local-versus-reference evidence comparison"),
                    confidence_before=0.38,
                    expected_value=0.67,
                    risk=0.24,
                    resource_need="local_first_reference_optional",
                    rationale="evidence acquisition used local artifacts successfully, but source diversity remains less urgent than transfer validation",
                    success_criteria=source_criteria,
                    evidence_requirements=("source_classification_record", "comparison_digest"),
                    prerequisite_graph={"source_diversity_inventory": (), "reference_evidence_comparison": ("source_diversity_inventory",)},
                )
            )
        communication_criteria = ("uncertainty_wording_check", "operator_state_alignment_check")
        if not _candidate_already_satisfied("developmental_communication_calibration", communication_criteria):
            candidates.append(
                DevelopmentalNextGoalCandidate(
                    candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "developmental_communication_calibration"),
                    normalized_objective="developmental_communication_calibration",
                    objective="Develop calibration checks for communicating developmental uncertainty to the operator",
                    evidence_basis=evidence_basis,
                    missing_evidence=("uncertainty wording calibration record", "operator-facing state comparison"),
                    confidence_before=0.52,
                    expected_value=0.52,
                    risk=0.16,
                    resource_need="runtime_state_and_message_comparison",
                    rationale="communication calibration matters, but current evidence shows transfer validity is the more material developmental risk",
                    success_criteria=communication_criteria,
                    evidence_requirements=("message_state_comparison", "calibration_disposition"),
                    prerequisite_graph={"uncertainty_wording_check": (), "operator_state_alignment_check": ("uncertainty_wording_check",)},
                )
            )
    inventory = capability_inventory_from_knowledge(knowledge_ledger)
    limitation_gaps = {str(item["gap_id"]): item for item in _limitation_gap_evidence(inventory)}
    if limitation_gaps:
        tracked_criteria = ("application_path_evidence_inventory", "tracked_integration_dry_run", "operator_application_boundary_validation")
        if "missing_tracked_application_proof" in limitation_gaps and not _candidate_already_satisfied("tracked_integration_proof", tracked_criteria):
            gap = limitation_gaps["missing_tracked_application_proof"]
            candidates.append(
                DevelopmentalNextGoalCandidate(
                    candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "tracked_integration_proof", tuple(gap["capabilities"])),
                    normalized_objective="tracked_integration_proof",
                    objective="Develop governed tracked-integration proof for locally validated capabilities",
                    evidence_basis=tuple(gap["capabilities"]),
                    missing_evidence=tuple(gap["reasons"]),
                    confidence_before=0.46,
                    expected_value=0.91,
                    risk=0.28,
                    resource_need=str(gap["recommended_resource"]),
                    rationale="capability records repeatedly say local success remains outside the governed tracked-source application path",
                    success_criteria=tracked_criteria,
                    evidence_requirements=("application_boundary_inventory", "dry_run_equivalence_record", "operator_gate_validation_record"),
                    prerequisite_graph={
                        "application_path_evidence_inventory": (),
                        "tracked_integration_dry_run": ("application_path_evidence_inventory",),
                        "operator_application_boundary_validation": ("tracked_integration_dry_run",),
                    },
                )
            )
        non_fixture_criteria = ("non_fixture_case_generation", "non_fixture_validation_metric", "fixture_to_non_fixture_regression_control")
        if "fixture_scoped_validation" in limitation_gaps and not _candidate_already_satisfied("non_fixture_evaluation", non_fixture_criteria):
            gap = limitation_gaps["fixture_scoped_validation"]
            candidates.append(
                DevelopmentalNextGoalCandidate(
                    candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "non_fixture_evaluation", tuple(gap["capabilities"])),
                    normalized_objective="non_fixture_evaluation",
                    objective="Develop non-fixture evaluation for locally validated developmental capabilities",
                    evidence_basis=tuple(gap["capabilities"]),
                    missing_evidence=tuple(gap["reasons"]),
                    confidence_before=0.48,
                    expected_value=0.76,
                    risk=0.22,
                    resource_need=str(gap["recommended_resource"]),
                    rationale="focused tests and fixture-scoped evidence do not prove broader behavior",
                    success_criteria=non_fixture_criteria,
                    evidence_requirements=("non_fixture_case_record", "validation_metric", "control_regression_record"),
                    prerequisite_graph={
                        "non_fixture_case_generation": (),
                        "non_fixture_validation_metric": ("non_fixture_case_generation",),
                        "fixture_to_non_fixture_regression_control": ("non_fixture_validation_metric",),
                    },
                )
            )
        transfer_criteria = ("missing_transfer_case_inventory", "transfer_gap_validation", "transfer_gap_reassessment")
        if "missing_transfer_evidence" in limitation_gaps and not _candidate_already_satisfied("broader_transfer_evidence", transfer_criteria):
            gap = limitation_gaps["missing_transfer_evidence"]
            candidates.append(
                DevelopmentalNextGoalCandidate(
                    candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "broader_transfer_evidence", tuple(gap["capabilities"])),
                    normalized_objective="broader_transfer_evidence",
                    objective="Develop broader transfer evidence for capabilities with missing transfer proof",
                    evidence_basis=tuple(gap["capabilities"]),
                    missing_evidence=tuple(gap["reasons"]),
                    confidence_before=0.44,
                    expected_value=0.72,
                    risk=0.2,
                    resource_need=str(gap["recommended_resource"]),
                    rationale="some capability records still lack positive transfer evidence",
                    success_criteria=transfer_criteria,
                    evidence_requirements=("transfer_gap_inventory", "transfer_validation_metric", "reassessment_record"),
                    prerequisite_graph={
                        "missing_transfer_case_inventory": (),
                        "transfer_gap_validation": ("missing_transfer_case_inventory",),
                        "transfer_gap_reassessment": ("transfer_gap_validation",),
                    },
                )
            )
    knowledge_reuse_criteria = (
        "knowledge_retrieval_index",
        "prior_failure_avoidance_check",
        "next_goal_evidence_reuse_record",
    )
    uncertainty_records = tuple(
        record
        for record in recovered_knowledge
        if capability_is_acquired(record)
        and (
            record.residual_uncertainty
            or record.failed_approaches
            or record.reusable_process_rules
        )
    )
    if not candidates and uncertainty_records and not _candidate_already_satisfied("capability_knowledge_reuse_validation", knowledge_reuse_criteria):
        evidence = tuple(dict.fromkeys(record.capability_id for record in uncertainty_records[-8:]))
        candidates.append(
            DevelopmentalNextGoalCandidate(
                candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "capability_knowledge_reuse_validation", evidence),
                normalized_objective="capability_knowledge_reuse_validation",
                objective="Develop validation that accumulated capability evidence is retrieved and used before selecting future work",
                evidence_basis=evidence,
                missing_evidence=(
                    "proof retained knowledge records influence next-goal selection",
                    "proof prior failed approaches are not repeated",
                    "proof reusable process rules are consulted before new work",
                ),
                confidence_before=0.41,
                expected_value=0.73,
                risk=0.18,
                resource_need="local_knowledge_ledger_mining",
                rationale=(
                    "the active frontier is empty after accepted boundaries, but the knowledge ledger contains residual uncertainty, failed approaches, "
                    "and reusable process rules that have not yet been proven to guide subsequent developmental choices"
                ),
                success_criteria=knowledge_reuse_criteria,
                evidence_requirements=("knowledge_index_record", "failed_strategy_filter_record", "next_goal_reuse_trace"),
                prerequisite_graph={
                    "knowledge_retrieval_index": (),
                    "prior_failure_avoidance_check": ("knowledge_retrieval_index",),
                    "next_goal_evidence_reuse_record": ("prior_failure_avoidance_check",),
                },
            )
        )
    resource_use_criteria = (
        "available_resource_inventory",
        "local_resource_selection_trace",
        "authority_boundary_resource_filter",
    )
    if (
        not candidates
        and "next_goal_evidence_reuse_record" in satisfied
        and not _candidate_already_satisfied("available_resource_utilization_validation", resource_use_criteria)
    ):
        candidates.append(
            DevelopmentalNextGoalCandidate(
                candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "available_resource_utilization_validation"),
                normalized_objective="available_resource_utilization_validation",
                objective="Develop validation that available local and governed resources are inventoried before declaring a developmental frontier empty",
                evidence_basis=("knowledge_retrieval_index", "prior_failure_avoidance_check", "next_goal_evidence_reuse_record"),
                missing_evidence=(
                    "resource inventory for local, source, model, and operator lanes",
                    "selection trace showing why local resources are used before authority requests",
                    "proof disabled API or protected scopes remain filtered out",
                ),
                confidence_before=0.39,
                expected_value=0.71,
                risk=0.19,
                resource_need="local_resource_inventory_first",
                rationale=(
                    "knowledge reuse is now validated, but an empty developmental frontier is still ambiguous unless the runtime proves it checked "
                    "available resources and filtered unavailable authority-controlled lanes before stopping"
                ),
                success_criteria=resource_use_criteria,
                evidence_requirements=("resource_inventory_record", "resource_selection_trace", "authority_filter_record"),
                prerequisite_graph={
                    "available_resource_inventory": (),
                    "local_resource_selection_trace": ("available_resource_inventory",),
                    "authority_boundary_resource_filter": ("local_resource_selection_trace",),
                },
            )
        )
    advisory_resource_criteria = (
        "local_model_advisory_probe",
        "reference_retrieval_probe",
        "resource_evidence_integration",
    )
    if (
        not candidates
        and "authority_boundary_resource_filter" in satisfied
        and not _candidate_already_satisfied("advisory_resource_evidence_integration", advisory_resource_criteria)
    ):
        candidates.append(
            DevelopmentalNextGoalCandidate(
                candidate_id=stable_id("next-main-goal-candidate", contract.mission_id, completed_goal.main_goal_id, "advisory_resource_evidence_integration"),
                normalized_objective="advisory_resource_evidence_integration",
                objective="Develop validation that advisory local-model and reference evidence can inform next-goal reasoning without gaining authority",
                evidence_basis=("available_resource_inventory", "local_resource_selection_trace", "authority_boundary_resource_filter"),
                missing_evidence=(
                    "local model advisory lane availability or unavailability record",
                    "bounded reference retrieval provenance record",
                    "integration trace showing resource outputs remain evidence only",
                ),
                confidence_before=0.37,
                expected_value=0.69,
                risk=0.2,
                resource_need="governed_local_model_and_reference_probe",
                rationale=(
                    "resource availability has been inventoried, but the runtime still needs proof that advisory model/reference evidence can be "
                    "used for understanding while remaining non-authoritative"
                ),
                success_criteria=advisory_resource_criteria,
                evidence_requirements=("local_model_advisory_record", "reference_provenance_record", "non_authoritative_integration_record"),
                prerequisite_graph={
                    "local_model_advisory_probe": (),
                    "reference_retrieval_probe": (),
                    "resource_evidence_integration": ("local_model_advisory_probe", "reference_retrieval_probe"),
                },
            )
        )
    return tuple(sorted(candidates, key=lambda item: (-item.score, item.normalized_objective)))


def select_developmental_next_goal_candidate(
    candidates: Sequence[DevelopmentalNextGoalCandidate],
) -> DevelopmentalNextGoalCandidate | None:
    if not candidates:
        return None
    return tuple(candidates)[0]


def main_goal_from_developmental_next_goal_candidate(
    contract: BroadMissionContract,
    completed_goal: MainGoalContract,
    candidate: DevelopmentalNextGoalCandidate,
    knowledge_ledger: Sequence[CapabilityKnowledgeRecord],
    candidates: Sequence[DevelopmentalNextGoalCandidate],
) -> MainGoalContract:
    gained = tuple(dict.fromkeys(record.capability_id for record in knowledge_ledger if capability_is_acquired(record)))
    alternatives = tuple(item.normalized_objective for item in candidates)
    ranking = ", ".join(f"{item.normalized_objective}:{item.score}" for item in candidates)
    return MainGoalContract(
        main_goal_id=stable_id("continuous-main-goal", contract.mission_id, candidate.normalized_objective, gained),
        parent_mission_id=contract.mission_id,
        original_objective=candidate.objective,
        normalized_objective=candidate.normalized_objective,
        success_criteria=candidate.success_criteria,
        evidence_requirements=candidate.evidence_requirements,
        prerequisite_graph=candidate.prerequisite_graph,
        known_subgoals=(),
        active_subgoal="",
        completed_subgoals=(),
        blocked_subgoals=(),
        rejected_strategies=(),
        newly_discovered_prerequisites=candidate.missing_evidence,
        residual_uncertainty="; ".join(candidate.missing_evidence),
        capability_changes=gained,
        disposition="active",
        completion_rationale=(
            f"selected from ranked developmental next-goal candidates after {completed_goal.main_goal_id}; "
            f"ranking={ranking}; selected_rationale={candidate.rationale}; resource_need={candidate.resource_need}"
        ),
        next_main_goal_candidates=alternatives,
    )


def derive_next_main_goal(contract: BroadMissionContract, completed_goal: MainGoalContract, knowledge_ledger: Sequence[CapabilityKnowledgeRecord]) -> MainGoalContract | None:
    gained = tuple(dict.fromkeys(record.capability_id for record in knowledge_ledger if capability_is_acquired(record)))
    if completed_goal.normalized_objective == "developmental_self_assessment":
        objective = compile_long_horizon_objective(contract.original_operator_goal)
        plan = derive_developmental_capability_plan(objective, capability_inventory_from_knowledge(knowledge_ledger))
        return main_goal_from_developmental_plan(contract, plan)
    if completed_goal.normalized_objective == "developmental_self_direction_evidence" and _is_developmental_direction(contract.original_operator_goal):
        objective = "Develop resource-backed insight seeking for uncertain next-goal formation"
        normalized = "resource_backed_developmental_insight"
        criteria = (
            "uncertainty_detection_for_goal_selection",
            "resource_question_formulation",
            "evidence_changed_plan_recording",
        )
        return MainGoalContract(
            main_goal_id=stable_id("continuous-main-goal", contract.mission_id, normalized, gained),
            parent_mission_id=contract.mission_id,
            original_objective=objective,
            normalized_objective=normalized,
            success_criteria=criteria,
            evidence_requirements=("uncertainty_record", "resource_question", "evidence_delta", "updated_plan_rationale"),
            prerequisite_graph={
                "uncertainty_detection_for_goal_selection": (),
                "resource_question_formulation": ("uncertainty_detection_for_goal_selection",),
                "evidence_changed_plan_recording": ("resource_question_formulation",),
            },
            known_subgoals=(),
            active_subgoal="",
            completed_subgoals=(),
            blocked_subgoals=(),
            rejected_strategies=(),
            newly_discovered_prerequisites=("resource_question_formulation",),
            residual_uncertainty="broad self-development still needs proof that uncertainty can trigger appropriate evidence seeking",
            capability_changes=gained,
            disposition="active",
            completion_rationale=f"derived after {completed_goal.main_goal_id} proved developmental self-direction evidence",
            next_main_goal_candidates=(),
        )
    if completed_goal.normalized_objective == "resource_backed_developmental_insight" and "articulate" in contract.original_operator_goal.lower():
        objective = "Develop grounded operator communication from authoritative runtime state"
        normalized = "grounded_operator_communication"
        criteria = (
            "state_grounded_progress_summary",
            "verified_vs_assumed_explanation",
            "authority_boundary_explanation",
        )
        return MainGoalContract(
            main_goal_id=stable_id("continuous-main-goal", contract.mission_id, normalized, gained),
            parent_mission_id=contract.mission_id,
            original_objective=objective,
            normalized_objective=normalized,
            success_criteria=criteria,
            evidence_requirements=("controller_snapshot", "capability_inventory", "operator_explanation", "authority_boundary_state"),
            prerequisite_graph={
                "state_grounded_progress_summary": (),
                "verified_vs_assumed_explanation": ("state_grounded_progress_summary",),
                "authority_boundary_explanation": ("state_grounded_progress_summary",),
            },
            known_subgoals=(),
            active_subgoal="",
            completed_subgoals=(),
            blocked_subgoals=(),
            rejected_strategies=(),
            newly_discovered_prerequisites=("operator_explanation",),
            residual_uncertainty="articulate self-development requires explanations that match authoritative runtime state",
            capability_changes=gained,
            disposition="active",
            completion_rationale=f"derived after {completed_goal.main_goal_id} because the broad objective explicitly requires articulate self-direction",
            next_main_goal_candidates=(),
        )
    if completed_goal.normalized_objective == "grounded_operator_communication" and _is_developmental_direction(contract.original_operator_goal):
        objective = "Develop meaningful-progress and stall detection for unattended developmental work"
        normalized = "meaningful_progress_stall_detection"
        criteria = (
            "meaningful_transition_tracking",
            "stalled_execution_detection",
            "observation_mode_reactivation_or_honest_block",
        )
        return MainGoalContract(
            main_goal_id=stable_id("continuous-main-goal", contract.mission_id, normalized, gained),
            parent_mission_id=contract.mission_id,
            original_objective=objective,
            normalized_objective=normalized,
            success_criteria=criteria,
            evidence_requirements=("transition_ledger", "stalled_execution_record", "observation_reactivation_or_block_record"),
            prerequisite_graph={
                "meaningful_transition_tracking": (),
                "stalled_execution_detection": ("meaningful_transition_tracking",),
                "observation_mode_reactivation_or_honest_block": ("stalled_execution_detection",),
            },
            known_subgoals=(),
            active_subgoal="",
            completed_subgoals=(),
            blocked_subgoals=(),
            rejected_strategies=(),
            newly_discovered_prerequisites=("stalled_execution_detection",),
            residual_uncertainty="unattended development must distinguish meaningful work from liveness before free-running claims",
            capability_changes=gained,
            disposition="active",
            completion_rationale=f"derived after {completed_goal.main_goal_id} because observation without meaningful work must be diagnosed instead of silently idling",
            next_main_goal_candidates=(),
        )
    if _is_developmental_direction(contract.original_operator_goal):
        candidates = derive_developmental_next_goal_candidates(contract, completed_goal, knowledge_ledger)
        selected = select_developmental_next_goal_candidate(candidates)
        if selected is not None:
            return main_goal_from_developmental_next_goal_candidate(contract, completed_goal, selected, knowledge_ledger, candidates)
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
    if "optimize your runtime continuously" in lowered:
        return True
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
    missing_requirements = tuple(item for item in requirements if item not in categories and item not in verified)
    limitation_gap_records = _limitation_gap_evidence(inventory)
    limitation_gaps = tuple(str(item["gap_id"]) for item in limitation_gap_records)
    missing = tuple(dict.fromkeys(missing_requirements + limitation_gaps))
    enabled: list[str] = []
    if "sandbox_execution" in categories or any("sandbox" in item for item in verified):
        enabled.append("isolated local candidate experimentation")
    if "governed_evidence_handling" in categories or any("evidence" in item for item in verified):
        enabled.append("evidence-backed prerequisite comparison")
    if "operator_boundary_handling" in categories or any("operator" in item for item in verified):
        enabled.append("operator-gated application decisions")
    if not enabled and verified:
        enabled.append("limited developmental reassessment from retained capability evidence")
    questions = tuple(
        dict.fromkeys(
            _confidence_questions_for_objective(objective, missing_requirements)
            + tuple(str(item["confidence_question"]) for item in limitation_gap_records)
        )
    )
    resources = tuple(
        dict.fromkeys(
            _recommended_resources_for_objective(objective, missing_requirements)
            + tuple(str(item["recommended_resource"]) for item in limitation_gap_records)
        )
    )
    confidence = 0.78 if verified and missing_requirements else 0.62 if missing_requirements else 0.88
    if limitation_gap_records:
        confidence = min(confidence, max(0.42, 0.82 - (0.04 * len(limitation_gap_records))))
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
        needs_additional_insight=confidence < 0.8 or bool(questions) or bool(limitation_gap_records),
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


def compile_behavioral_failure_record(
    evidence: Mapping[str, Any],
    *,
    existing_records: Sequence[BehavioralFailureRecord | Mapping[str, Any]] = (),
) -> BehavioralFailureCompilationResult:
    if _contains_forbidden_failure_payload(evidence):
        return _behavioral_failure_rejection("forbidden_candidate_or_patch_content", (), evidence)
    source_type = _clean_token(evidence.get("source_type"))
    if source_type not in BEHAVIORAL_FAILURE_SOURCE_TYPES:
        return _behavioral_failure_rejection("unsupported_source_type", ("source_type",), evidence)
    source_classification = classify_behavioral_failure_source(source_type)
    if source_classification in {"activity_liveness_only", "invalid_developmental_evidence"}:
        return _behavioral_failure_rejection(f"{source_classification}_source", (), evidence, source_classification=source_classification)
    expected_authority = _clean_token(evidence.get("expected_behavior_authority"))
    if expected_authority not in EXPECTED_BEHAVIOR_AUTHORITIES:
        return _behavioral_failure_rejection("expected_behavior_authority_not_accepted", ("expected_behavior_authority",), evidence, source_classification=source_classification)
    missing = _missing_behavioral_failure_fields(evidence)
    if missing:
        return _behavioral_failure_rejection("missing_required_behavioral_failure_fields", missing, evidence, source_classification=source_classification)

    source_reference = _clean_text(evidence.get("source_reference"))
    observed = _clean_text(evidence.get("observed_behavior"))
    expected = _clean_text(evidence.get("expected_behavior"))
    expected_identity = _clean_token(evidence.get("expected_behavior_identity"))
    comparison = _clean_token(evidence.get("expected_vs_observed_result"))
    first_transition = _clean_text(evidence.get("first_incorrect_transition"))
    stage = _clean_token(evidence.get("affected_runtime_stage"))
    capability = _clean_token(evidence.get("affected_capability_id"))
    materiality = _clean_text(evidence.get("materiality_reason"))
    reproducibility = _clean_token(evidence.get("reproducibility_status"))
    authority = _clean_token(evidence.get("authority_class"))
    ambiguity = _clean_token(evidence.get("ambiguity_status"))
    disposition = _clean_token(evidence.get("current_disposition") or "observed")
    if reproducibility not in REPRODUCIBILITY_STATUSES:
        return _behavioral_failure_rejection("unsupported_reproducibility_status", ("reproducibility_status",), evidence, source_classification=source_classification)
    if authority not in AUTHORITY_CLASSES:
        return _behavioral_failure_rejection("unsupported_authority_class", ("authority_class",), evidence, source_classification=source_classification)
    if ambiguity not in AMBIGUITY_STATUSES:
        return _behavioral_failure_rejection("unsupported_ambiguity_status", ("ambiguity_status",), evidence, source_classification=source_classification)
    if disposition not in BEHAVIORAL_FAILURE_DISPOSITIONS:
        return _behavioral_failure_rejection("unsupported_current_disposition", ("current_disposition",), evidence, source_classification=source_classification)

    attempts = _compile_reproduction_attempts(evidence)
    if attempts is None:
        return _behavioral_failure_rejection("invalid_reproduction_attempts", ("reproduction_attempts",), evidence, source_classification=source_classification)
    owner_paths = _clean_tuple(evidence.get("suspected_owner_paths"))
    independent_paths = _clean_tuple(evidence.get("independent_evidence_paths"))
    allowed_scope = _clean_tuple(evidence.get("allowed_scope"))
    excluded_scope = _clean_tuple(evidence.get("excluded_scope")) or PROTECTED_PATH_PATTERNS
    source_digest = _clean_token(evidence.get("source_digest"))
    environment_digest = _clean_token(evidence.get("environment_digest"))
    state_digest = _clean_token(evidence.get("state_digest"))
    reproduction_output_digest = _clean_token(evidence.get("reproduction_output_digest"))
    evidence_digest = stable_id(
        "behavioral-failure-evidence",
        source_type,
        source_reference,
        source_digest,
        expected_identity,
        expected,
        observed,
        comparison,
        tuple(attempt.as_dict() for attempt in attempts),
        first_transition,
        stage,
        capability,
        owner_paths,
        independent_paths,
        environment_digest,
        state_digest,
        reproduction_output_digest,
    )
    semantic_key = stable_id(
        "behavioral-failure-semantic-key",
        expected_identity,
        _deviation_class(comparison, observed),
        first_transition,
        stage,
        capability,
        owner_paths,
        independent_paths,
    )
    sealed_digest = stable_id(
        "sealed-behavioral-failure-bundle",
        source_type,
        source_reference,
        source_digest,
        expected_identity,
        expected,
        observed,
        comparison,
        tuple(attempt.as_dict() for attempt in attempts),
        first_transition,
        stage,
        capability,
        owner_paths,
        independent_paths,
        allowed_scope,
        excluded_scope,
        environment_digest,
        state_digest,
        authority,
        ambiguity,
    )
    existing = tuple(_as_behavioral_failure_record(item) for item in existing_records)
    same_semantic = [item for item in existing if item.semantic_failure_key == semantic_key]
    duplicate = next((item for item in same_semantic if item.evidence_digest == evidence_digest), None)
    version_parent = next((item for item in same_semantic if item.evidence_digest != evidence_digest), None)
    now = _clean_text(evidence.get("observed_at")) or utc_now()
    first_seen = version_parent.first_seen if version_parent is not None else now
    occurrence_count = (max((item.occurrence_count for item in same_semantic), default=0) + 1) if duplicate is None else duplicate.occurrence_count
    eligibility = _classify_task_eligibility(
        source_classification=source_classification,
        reproducibility_status=reproducibility,
        authority_class=authority,
        ambiguity_status=ambiguity,
        expected_behavior_identity=expected_identity,
        first_incorrect_transition=first_transition,
        owner_paths=owner_paths,
    )
    current = "closed_duplicate" if duplicate is not None else ("task_eligible" if eligibility == "eligible" else _disposition_from_reproducibility(reproducibility))
    record = BehavioralFailureRecord(
        failure_id=duplicate.failure_id if duplicate is not None else stable_id("behavioral-failure", semantic_key, evidence_digest),
        semantic_failure_key=semantic_key,
        source_type=source_type,
        source_reference=source_reference,
        source_digest=source_digest,
        observed_behavior=observed,
        expected_behavior=expected,
        expected_behavior_identity=expected_identity,
        expected_vs_observed_result=comparison,
        baseline_reproduction=_clean_text(evidence.get("baseline_reproduction")),
        reproduction_command_or_predicate=_clean_text(evidence.get("reproduction_command_or_predicate")),
        reproduction_attempts=tuple(attempt.as_dict() for attempt in attempts),
        reproduction_result=_clean_token(evidence.get("reproduction_result")),
        reproduction_output_digest=reproduction_output_digest,
        first_incorrect_transition=first_transition,
        affected_runtime_stage=stage,
        affected_capability_id=capability,
        originating_mission_id=_clean_token(evidence.get("originating_mission_id")),
        suspected_owner_paths=owner_paths,
        independent_evidence_paths=independent_paths,
        allowed_scope=allowed_scope,
        excluded_scope=excluded_scope,
        materiality_reason=materiality,
        reproducibility_status=reproducibility,
        occurrence_count=occurrence_count,
        first_seen=first_seen,
        last_seen=now,
        environment_digest=environment_digest,
        state_digest=state_digest,
        evidence_digest=evidence_digest,
        sealed_failure_bundle_digest=sealed_digest,
        authority_class=authority,
        ambiguity_status=ambiguity,
        task_eligibility="ineligible_duplicate" if duplicate is not None else eligibility,
        current_disposition=current,
        duplicate_of=duplicate.failure_id if duplicate is not None else "",
        version_of=version_parent.failure_id if version_parent is not None and duplicate is None else "",
        advisory_model_digest=_clean_token(evidence.get("advisory_model_digest")),
        closure_reason=_clean_text(evidence.get("closure_reason")),
        closed_at=_clean_text(evidence.get("closed_at")),
    )
    return BehavioralFailureCompilationResult(
        accepted=True,
        record=record,
        rejection_reason="",
        missing_fields=(),
        source_classification=source_classification,
        duplicate_of=record.duplicate_of,
        version_of=record.version_of,
    )


def behavioral_failure_to_runtime_finding(record: BehavioralFailureRecord | Mapping[str, Any]) -> RuntimeFinding:
    failure = _as_behavioral_failure_record(record)
    diagnostic_only = failure.task_eligibility != "eligible"
    return RuntimeFinding(
        finding_id=stable_id("runtime-finding-from-behavioral-failure", failure.failure_id, failure.sealed_failure_bundle_digest),
        evidence_source=f"behavioral_failure:{failure.failure_id}:{failure.sealed_failure_bundle_digest}",
        observed_behavior=failure.observed_behavior,
        first_incorrect_transition=failure.first_incorrect_transition,
        affected_capability=failure.affected_capability_id,
        baseline_metric=failure.baseline_reproduction or failure.reproduction_result,
        confidence=0.9 if failure.reproducibility_status == "reproduced" else 0.65,
        uncertainty=f"{failure.ambiguity_status}; sealed_failure_bundle={failure.sealed_failure_bundle_digest}",
        scope=",".join(failure.allowed_scope) or "local_runtime",
        operator_value=0.8 if failure.task_eligibility == "eligible" else 0.4,
        severity=0.8 if failure.task_eligibility == "eligible" else 0.3,
        estimated_implementation_breadth="small",
        validation_method=f"behavioral_failure_record:{failure.expected_behavior_identity}",
        diagnostic_only=diagnostic_only,
    )


def classify_behavioral_failure_source(source_type: str) -> str:
    if source_type in STRONG_BEHAVIORAL_FAILURE_SOURCES:
        return "strong_behavioral_evidence"
    if source_type in {"durable_runtime_failure", "runtime_exception", "user_visible_reproduction"}:
        return "potentially_strong_after_reproduction"
    if source_type in {"operator_report"}:
        return "weak_corroborating_evidence"
    if source_type == "model_advisory":
        return "invalid_developmental_evidence"
    if source_type == "activity_artifact":
        return "activity_liveness_only"
    return "structural_evidence_only"


def _missing_behavioral_failure_fields(evidence: Mapping[str, Any]) -> tuple[str, ...]:
    required = (
        "source_reference",
        "source_digest",
        "observed_behavior",
        "expected_behavior",
        "expected_behavior_identity",
        "expected_vs_observed_result",
        "baseline_reproduction",
        "reproduction_command_or_predicate",
        "reproduction_attempts",
        "reproduction_result",
        "reproduction_output_digest",
        "first_incorrect_transition",
        "affected_runtime_stage",
        "affected_capability_id",
        "suspected_owner_paths",
        "independent_evidence_paths",
        "allowed_scope",
        "materiality_reason",
        "reproducibility_status",
        "environment_digest",
        "state_digest",
        "authority_class",
        "ambiguity_status",
    )
    return tuple(name for name in required if _is_empty_failure_value(evidence.get(name)))


def _compile_reproduction_attempts(evidence: Mapping[str, Any]) -> tuple[ReproductionAttemptRecord, ...] | None:
    attempts: list[ReproductionAttemptRecord] = []
    for index, raw in enumerate(evidence.get("reproduction_attempts") or ()):
        if not isinstance(raw, Mapping):
            return None
        command = _clean_text(raw.get("command_or_predicate_identity") or raw.get("predicate") or raw.get("command"))
        state_ref = _clean_text(raw.get("input_or_state_reference") or raw.get("state_reference"))
        status = _clean_token(raw.get("status"))
        classification = _clean_token(raw.get("result_classification") or raw.get("classification"))
        if not command or not state_ref or not status or not classification:
            return None
        attempts.append(
            ReproductionAttemptRecord(
                attempt_id=_clean_token(raw.get("attempt_id")) or stable_id("reproduction-attempt", command, state_ref, status, classification, index),
                command_or_predicate_identity=command,
                input_or_state_reference=state_ref,
                started_at=_clean_text(raw.get("started_at")) or "not_recorded",
                completed_at=_clean_text(raw.get("completed_at")) or "not_recorded",
                status=status,
                result_classification=classification,
                stdout_digest=_clean_token(raw.get("stdout_digest")),
                stderr_digest=_clean_token(raw.get("stderr_digest")),
                result_digest=_clean_token(raw.get("result_digest")) or stable_id("reproduction-result", command, state_ref, status, classification),
                timeout_or_resource_result=_clean_text(raw.get("timeout_or_resource_result")),
                environment_digest=_clean_token(raw.get("environment_digest") or evidence.get("environment_digest")),
                safety_boundary=_clean_text(raw.get("safety_boundary")) or "local_deterministic_no_mutation",
                authoritative_runner_identity=_clean_text(raw.get("authoritative_runner_identity")) or "unspecified_runner",
            )
        )
    return tuple(attempts)


def _classify_task_eligibility(
    *,
    source_classification: str,
    reproducibility_status: str,
    authority_class: str,
    ambiguity_status: str,
    expected_behavior_identity: str,
    first_incorrect_transition: str,
    owner_paths: tuple[str, ...],
) -> str:
    if source_classification == "activity_liveness_only":
        return "ineligible_activity_only"
    if not expected_behavior_identity:
        return "ineligible_missing_expectation"
    if not first_incorrect_transition:
        return "ineligible_missing_transition"
    if reproducibility_status not in {"reproduced", "intermittently_reproduced"}:
        return "ineligible_unreproduced"
    if authority_class == "operator_authority_required":
        return "blocked_authority"
    if authority_class == "protected_scope":
        return "blocked_authority"
    if authority_class == "resource_blocked":
        return "blocked_resource"
    if authority_class == "accepted_boundary":
        return "ineligible_accepted_boundary"
    if ambiguity_status in {"unresolved_material_ambiguity", "missing_expected_behavior", "missing_owner_scope", "conflicting_evidence"}:
        return "unresolved_ambiguity"
    if not owner_paths:
        return "ineligible_missing_transition"
    if source_classification in {"structural_evidence_only", "weak_corroborating_evidence"}:
        return "ineligible_structural_only"
    return "eligible"


def _disposition_from_reproducibility(reproducibility_status: str) -> str:
    if reproducibility_status == "reproduced":
        return "reproducible_material_failure"
    if reproducibility_status == "intermittently_reproduced":
        return "intermittent_material_failure"
    if reproducibility_status == "reproduction_pending":
        return "reproduction_pending"
    return "insufficient_evidence"


def _behavioral_failure_rejection(
    reason: str,
    missing_fields: Sequence[str],
    evidence: Mapping[str, Any],
    *,
    source_classification: str | None = None,
) -> BehavioralFailureCompilationResult:
    return BehavioralFailureCompilationResult(
        accepted=False,
        record=None,
        rejection_reason=reason,
        missing_fields=tuple(missing_fields),
        source_classification=source_classification or classify_behavioral_failure_source(_clean_token(evidence.get("source_type"))),
    )


def _as_behavioral_failure_record(record: BehavioralFailureRecord | Mapping[str, Any]) -> BehavioralFailureRecord:
    if isinstance(record, BehavioralFailureRecord):
        return record
    return BehavioralFailureRecord(**dict(record))


def _contains_forbidden_failure_payload(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_BEHAVIORAL_FAILURE_KEYS:
                return True
            if _contains_forbidden_failure_payload(item):
                return True
    elif isinstance(value, (tuple, list)):
        return any(_contains_forbidden_failure_payload(item) for item in value)
    return False


def _deviation_class(comparison: str, observed: str) -> str:
    normalized = _clean_token(comparison)
    if normalized:
        return normalized
    lowered = " ".join(_clean_text(observed).lower().split())
    for token in ("exception", "timeout", "wrong_state", "missing_output", "regression", "denied"):
        if token.replace("_", " ") in lowered or token in lowered:
            return token
    return "observed_deviation"


def _is_empty_failure_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (tuple, list, dict)):
        return not value
    return False


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _clean_token(value: Any) -> str:
    return _clean_text(value).lower().replace(" ", "_")


def _clean_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_clean_text(value),) if value.strip() else ()
    return tuple(item for item in (_clean_text(item) for item in value) if item)


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
    solved = {record.capability_id for record in knowledge_ledger if capability_is_acquired(record)}
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
        reassessment="behaviorally_demonstrated",
        residual_uncertainty="limited to current dependency id grammar",
        reusable_process_rules=("sandbox success requires clean reproduction", "path hardening must avoid manual PYTHONPATH"),
        evidence_stage="behaviorally_demonstrated",
        capability_acquired=True,
        eligible_for_behavioral_evaluation=False,
        behavioral_evaluation_ref="LIVE45_TRANSFER_BEHAVIORAL_EVALUATION",
        behavioral_evaluation={
            "evaluation_id": "LIVE45_TRANSFER_BEHAVIORAL_EVALUATION",
            "task_family_id": "transfer_dependency_identity_preservation",
            "disposition": "behaviorally_demonstrated",
            "evidence_independence": {"case_source": "sealed", "self_reported_success": False},
        },
    )
