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
