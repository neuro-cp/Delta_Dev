"""RC3 governed goal/planning foundation state.

The objects in this module are inert state frames. They serialize RC3 thinking
without enabling execution, persistence, providers, plugins, sandboxes, commits,
pushes, or production mutation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_JSON = ROOT / "reports" / "RC3_MILESTONE_1_FOUNDATION.json"
REPORT_MD = ROOT / "reports" / "RC3_MILESTONE_1_FOUNDATION.md"

SAFETY_DEFAULTS: dict[str, bool] = {
    "provider_calls_performed": False,
    "web_search_performed": False,
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_write_performed": False,
    "graph_write_performed": False,
    "replay_write_performed": False,
    "autonomous_action_performed": False,
    "scheduler_action_performed": False,
    "plan_execution_performed": False,
    "tool_execution_performed": False,
    "plugin_creation_performed": False,
    "plugin_activation_performed": False,
    "sandbox_creation_performed": False,
    "automatic_commit_performed": False,
    "automatic_push_performed": False,
    "deployment_performed": False,
    "production_mutation_performed": False,
    "hidden_persistence_performed": False,
    "delta_75_interaction_performed": False,
    "hyb1_promoted": False,
    "model_b_replaced": False,
}


@dataclass(frozen=True)
class GoalFrame:
    goal_id: str
    source_user_text: str
    normalized_objective: str
    goal_type: str
    explicitness: str
    success_criteria: tuple[str, ...]
    constraints: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    assumptions: tuple[str, ...]
    dependencies: tuple[str, ...]
    requested_resources: tuple[str, ...]
    permitted_tools: tuple[str, ...]
    prohibited_tools: tuple[str, ...]
    priority: float
    status: str
    confidence: float
    uncertainty: str
    operator_confirmation_status: str
    persistence_status: str
    provenance: dict[str, Any]
    creation_turn: str
    last_updated_turn: str
    parent_goal: str | None = None
    child_goals: tuple[str, ...] = ()
    superseded_goal: str | None = None
    completion_evidence: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class PlanStepFrame:
    step_id: str
    summary: str
    dependency_ids: tuple[str, ...]
    preserves_constraints: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    expected_evidence: tuple[str, ...]
    risk: str
    uncertainty: str
    non_executing: bool = True


@dataclass(frozen=True)
class PlanFrame:
    plan_id: str
    goal_id: str
    strategy: str
    lifecycle_state: str
    steps: tuple[PlanStepFrame, ...]
    constraints_preserved: tuple[str, ...]
    dependencies: tuple[str, ...]
    risks: tuple[str, ...]
    assumptions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    execution_authorized: bool
    persistence_status: str
    provenance: dict[str, Any]
    confidence: float
    uncertainty: str
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class GoalPlanArbitration:
    arbitration_id: str
    goal_id: str
    plan_id: str
    status: str
    selected: bool
    conflicts: tuple[str, ...]
    rejected_reasons: tuple[str, ...]
    constraint_checks: tuple[str, ...]
    decision_reason: str
    operator_approval_required_before_action: bool
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class IntrospectionSnapshot:
    snapshot_id: str
    claims: tuple[dict[str, str], ...]
    assumptions: tuple[str, ...]
    uncertainty: tuple[str, ...]
    fabricated_self_state: bool
    hidden_state_detected: bool
    evidence_sources: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class ProgressEvaluation:
    evaluation_id: str
    goal_id: str
    plan_id: str
    status: str
    completion_score: float
    completion_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    failure_signals: tuple[str, ...]
    completion_requires_operator_confirmation: bool
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class CapabilityGapAssessment:
    assessment_id: str
    goal_id: str
    plan_id: str
    requested_capabilities: tuple[str, ...]
    existing_capability_matches: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    plugin_needed: bool
    sandbox_needed: bool
    proposal_needed: bool
    recommendation: str
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class RC3Episode:
    episode_id: str
    created_at: str
    source_text: str
    rc2_episode_reference: str | None
    goal_frame: GoalFrame
    plan_frame: PlanFrame
    arbitration: GoalPlanArbitration
    introspection: IntrospectionSnapshot
    progress: ProgressEvaluation
    capability_gap: CapabilityGapAssessment
    developer_overlay: dict[str, Any]
    persistence_status: str
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_rc3_foundation_episode(source_text: str, *, rc2_episode_reference: str | None = None) -> RC3Episode:
    """Build an inert RC3 foundation episode from explicit operator text."""

    normalized = _normalize_objective(source_text)
    turn_id = _stable_id("turn", source_text)
    goal = GoalFrame(
        goal_id=_stable_id("goal", source_text),
        source_user_text=source_text,
        normalized_objective=normalized,
        goal_type=_classify_goal_type(source_text),
        explicitness=_explicitness(source_text),
        success_criteria=_extract_success_criteria(source_text),
        constraints=_extract_constraints(source_text),
        prohibited_actions=_extract_prohibitions(source_text),
        assumptions=_extract_assumptions(source_text),
        dependencies=(),
        requested_resources=_extract_resources(source_text),
        permitted_tools=(),
        prohibited_tools=_extract_prohibited_tools(source_text),
        priority=0.5,
        status="interpreted",
        confidence=0.78 if _explicitness(source_text) == "explicit" else 0.52,
        uncertainty="moderate" if _explicitness(source_text) == "explicit" else "high_clarification_recommended",
        operator_confirmation_status="not_confirmed",
        persistence_status="ephemeral",
        provenance={"source": "operator_text", "extraction": "deterministic_rc3_foundation_scaffold"},
        creation_turn=turn_id,
        last_updated_turn=turn_id,
    )
    steps = (
        PlanStepFrame(
            step_id=_stable_id("step", source_text, "interpret"),
            summary="Interpret the explicit objective and constraints.",
            dependency_ids=(),
            preserves_constraints=goal.constraints,
            prohibited_actions=goal.prohibited_actions,
            expected_evidence=("goal_frame", "constraint_list"),
            risk="low",
            uncertainty=goal.uncertainty,
        ),
        PlanStepFrame(
            step_id=_stable_id("step", source_text, "plan"),
            summary="Create a non-executing plan for operator review.",
            dependency_ids=(_stable_id("step", source_text, "interpret"),),
            preserves_constraints=goal.constraints,
            prohibited_actions=goal.prohibited_actions,
            expected_evidence=("plan_frame", "dependency_notes"),
            risk="low",
            uncertainty="moderate",
        ),
        PlanStepFrame(
            step_id=_stable_id("step", source_text, "evaluate"),
            summary="Evaluate progress using evidence before claiming completion.",
            dependency_ids=(_stable_id("step", source_text, "plan"),),
            preserves_constraints=goal.constraints,
            prohibited_actions=goal.prohibited_actions,
            expected_evidence=("progress_evaluation", "missing_evidence"),
            risk="low",
            uncertainty="moderate",
        ),
    )
    plan = PlanFrame(
        plan_id=_stable_id("plan", source_text),
        goal_id=goal.goal_id,
        strategy="read_only_goal_planning_foundation",
        lifecycle_state="draft",
        steps=steps,
        constraints_preserved=goal.constraints,
        dependencies=("operator_confirmation",),
        risks=("Premature execution would violate RC3 foundation boundaries.",),
        assumptions=goal.assumptions,
        prohibited_actions=goal.prohibited_actions,
        execution_authorized=False,
        persistence_status="ephemeral",
        provenance={"source_goal_id": goal.goal_id, "planner": "deterministic_rc3_foundation_scaffold"},
        confidence=0.74,
        uncertainty="moderate",
    )
    arbitration = GoalPlanArbitration(
        arbitration_id=_stable_id("arbitration", source_text),
        goal_id=goal.goal_id,
        plan_id=plan.plan_id,
        status="accepted_read_only",
        selected=True,
        conflicts=(),
        rejected_reasons=(),
        constraint_checks=tuple(f"preserved: {item}" for item in goal.constraints) or ("no_explicit_constraints_found",),
        decision_reason="The plan is read-only, non-executing, and preserves known prohibitions.",
        operator_approval_required_before_action=True,
    )
    introspection = IntrospectionSnapshot(
        snapshot_id=_stable_id("snapshot", source_text),
        claims=(
            {"claim": "RC3 foundation objects are ephemeral.", "evidence": "docs/RC3_STATE_MODEL.md"},
            {"claim": "Plan execution is not authorized.", "evidence": "PlanFrame.execution_authorized=false"},
            {"claim": "RC2 remains the answer-this-turn substrate.", "evidence": "docs/RC2_COGNITIVE_PIPELINE_SPECIFICATION.md"},
        ),
        assumptions=("Source text contains the operator's current objective.",),
        uncertainty=("No operator confirmation has been recorded in this ephemeral episode.",),
        fabricated_self_state=False,
        hidden_state_detected=False,
        evidence_sources=("docs/RC3_STATE_MODEL.md", "docs/RC2_COGNITIVE_PIPELINE_SPECIFICATION.md"),
    )
    progress = ProgressEvaluation(
        evaluation_id=_stable_id("progress", source_text),
        goal_id=goal.goal_id,
        plan_id=plan.plan_id,
        status="needs_evidence",
        completion_score=0.0,
        completion_evidence=(),
        missing_evidence=("operator_confirmation", "implementation_evidence", "validation_results"),
        blockers=(),
        failure_signals=(),
        completion_requires_operator_confirmation=True,
    )
    capability_gap = CapabilityGapAssessment(
        assessment_id=_stable_id("gap", source_text),
        goal_id=goal.goal_id,
        plan_id=plan.plan_id,
        requested_capabilities=_extract_requested_capabilities(source_text),
        existing_capability_matches=("RC2 cognitive pipeline", "RC3 protocol scaffold"),
        missing_capabilities=("persistent RC3 project state", "sandbox runtime", "plugin activation workflow"),
        plugin_needed=False,
        sandbox_needed=False,
        proposal_needed=True,
        recommendation="Begin with RC3-A goal/planning scaffold before engineering plugins or sandboxes.",
    )
    episode = RC3Episode(
        episode_id=_stable_id("rc3", source_text),
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        source_text=source_text,
        rc2_episode_reference=rc2_episode_reference,
        goal_frame=goal,
        plan_frame=plan,
        arbitration=arbitration,
        introspection=introspection,
        progress=progress,
        capability_gap=capability_gap,
        developer_overlay={
            "rc3_state_model": "docs/RC3_STATE_MODEL.md",
            "goal_id": goal.goal_id,
            "plan_id": plan.plan_id,
            "arbitration_id": arbitration.arbitration_id,
            "execution_authorized": False,
            "persistence_status": "ephemeral",
        },
        persistence_status="ephemeral",
    )
    return episode


def build_rc3_milestone_1_foundation_report(write_reports: bool = True) -> dict[str, Any]:
    episode = build_rc3_foundation_episode(
        "Design RC3 Milestone 1 with governed goals, read-only planning, introspection, progress evaluation, and capability gap analysis. Do not execute plans or touch DELTA-75."
    )
    payload = episode.to_dict()
    report = {
        "report": "RC3_MILESTONE_1_FOUNDATION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "state_model": "docs/RC3_STATE_MODEL.md",
        "scope": "ephemeral_goal_planning_introspection_foundation",
        "episode": payload,
        "legacy_code_classification": {
            "orchestration.agency.goal_system": "legacy_reference_only_for_now",
            "orchestration.agency.planning_engine": "legacy_reference_only_for_now",
            "orchestration.runtime.rc3_operator_pilot_freeze_readiness": "reusable_protocol_scaffold",
            "docs.RC2_COGNITIVE_PIPELINE_SPECIFICATION": "stable_foundation_contract",
            "docs.RC2_ROUTING_PRECEDENCE": "stable_foundation_contract",
        },
        "validation_claims": {
            "objects_ephemeral": _all_ephemeral(payload),
            "no_execution_authorized": episode.plan_frame.execution_authorized is False,
            "safety_all_false": all(value is False for value in episode.safety.values()),
            "developer_overlay_available": bool(episode.developer_overlay),
            "capability_gap_present": bool(episode.capability_gap.missing_capabilities),
        },
        "safety": dict(SAFETY_DEFAULTS),
        "recommendation": "READY_FOR_FOCUSED_RC3_A_GOAL_AND_PLANNING_SCAFFOLD_IMPLEMENTATION",
    }
    if write_reports:
        _write_report(report)
    return report


def _normalize_objective(text: str) -> str:
    clean = " ".join(text.strip().split())
    clean = re.sub(r"\bplease\b", "", clean, flags=re.IGNORECASE).strip()
    return clean[:220]


def _classify_goal_type(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ("do not", "don't", "never", "avoid")):
        return "project_objective_with_prohibitions"
    if any(term in lower for term in ("design", "build", "implement", "create")):
        return "project_objective"
    if any(term in lower for term in ("remember", "prefer", "i like")):
        return "preference"
    return "conversational_objective"


def _explicitness(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in ("design", "build", "implement", "create", "do not", "don't", "must")):
        return "explicit"
    return "implicit_or_ambiguous"


def _extract_success_criteria(text: str) -> tuple[str, ...]:
    lower = text.lower()
    criteria: list[str] = []
    if "report" in lower:
        criteria.append("report generated")
    if "test" in lower or "validation" in lower:
        criteria.append("focused validation passed")
    if "commit" in lower:
        criteria.append("checkpoint committed only if operator requested")
    if not criteria:
        criteria.append("operator confirms objective was understood")
    return tuple(criteria)


def _extract_constraints(text: str) -> tuple[str, ...]:
    constraints: list[str] = []
    lower = text.lower()
    if "no execution" in lower or "do not execute" in lower:
        constraints.append("no execution")
    if "read-only" in lower or "read only" in lower:
        constraints.append("read-only")
    if "ephemeral" in lower:
        constraints.append("ephemeral by default")
    if "do not" in lower or "don't" in lower:
        constraints.append("preserve explicit prohibitions")
    return tuple(dict.fromkeys(constraints))


def _extract_prohibitions(text: str) -> tuple[str, ...]:
    lower = text.lower()
    prohibitions = []
    mapping = {
        "delta-75": "do not interact with DELTA-75",
        "execute": "do not execute plans",
        "provider": "do not invoke providers",
        "plugin": "do not activate plugins",
        "sandbox": "do not create sandboxes",
        "canonical": "do not write canonical memory",
        "noncanonical": "do not write noncanonical substrate memory",
        "push": "do not push unless explicitly requested",
        "commit": "do not commit unless explicitly requested",
    }
    for term, value in mapping.items():
        if term in lower and ("do not" in lower or "don't" in lower or "no " in lower):
            prohibitions.append(value)
    return tuple(dict.fromkeys(prohibitions))


def _extract_assumptions(text: str) -> tuple[str, ...]:
    return ("RC2 remains frozen and available as the answer-this-turn runtime.",)


def _extract_resources(text: str) -> tuple[str, ...]:
    lower = text.lower()
    resources = []
    for term in ("docs", "reports", "tests", "developer overlay", "state model"):
        if term in lower:
            resources.append(term)
    return tuple(resources)


def _extract_prohibited_tools(text: str) -> tuple[str, ...]:
    lower = text.lower()
    tools = []
    if "provider" in lower:
        tools.append("providers")
    if "web" in lower:
        tools.append("web")
    if "plugin" in lower:
        tools.append("plugins")
    if "sandbox" in lower:
        tools.append("sandboxes")
    return tuple(tools)


def _extract_requested_capabilities(text: str) -> tuple[str, ...]:
    lower = text.lower()
    capabilities = []
    for term in ("goals", "planning", "introspection", "progress evaluation", "capability gap", "developer overlay"):
        if term in lower:
            capabilities.append(term)
    return tuple(capabilities) or ("goal interpretation", "read-only planning")


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"rc3-{prefix}-{digest}"


def _all_ephemeral(payload: dict[str, Any]) -> bool:
    serialized = json.dumps(payload, sort_keys=True)
    return '"persistence_status": "ephemeral"' in serialized


def _write_report(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3 Milestone 1 Foundation",
        "",
        f"Created: {report['created_at']}",
        f"Scope: {report['scope']}",
        f"State model: {report['state_model']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Validation Claims",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["validation_claims"].items())
    lines.extend(["", "## Legacy Code Classification", ""])
    lines.extend(f"- {key}: {value}" for key, value in report["legacy_code_classification"].items())
    lines.extend([
        "",
        "## Episode Summary",
        "",
        f"- Goal: {report['episode']['goal_frame']['normalized_objective']}",
        f"- Goal type: {report['episode']['goal_frame']['goal_type']}",
        f"- Plan: {report['episode']['plan_frame']['strategy']}",
        f"- Progress status: {report['episode']['progress']['status']}",
        f"- Capability recommendation: {report['episode']['capability_gap']['recommendation']}",
        "",
        "## Safety",
        "",
    ])
    lines.extend(f"- {key}: {value}" for key, value in report["safety"].items())
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_rc3_milestone_1_foundation_report(write_reports=True)
    print(json.dumps({
        "recommendation": report["recommendation"],
        "state_model": report["state_model"],
        "objects_ephemeral": report["validation_claims"]["objects_ephemeral"],
        "no_execution_authorized": report["validation_claims"]["no_execution_authorized"],
        "safety_all_false": report["validation_claims"]["safety_all_false"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
