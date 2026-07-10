"""Governed RC3-B plan revision scaffold.

This module decides whether a read-only plan should change, creates bounded
revised PlanFrame objects, compares them, and records an ephemeral revision
trace. It never executes a plan, persists a plan, creates plugins, creates
sandboxes, calls providers, commits, pushes, deploys, or touches DELTA-75.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc3_capability_gap_analyzer import analyze_capability_gap
from orchestration.runtime.rc3_episode_builder import build_rc3_goal_planning_episode
from orchestration.runtime.rc3_foundation_renderer import render_rc3_foundation_summary
from orchestration.runtime.rc3_foundation_state import (
    CapabilityGapAssessment,
    GoalFrame,
    PlanFrame,
    PlanStepFrame,
    ProgressEvaluation,
    RC3Episode,
    SAFETY_DEFAULTS,
    _stable_id,
)
from orchestration.runtime.rc3_goal_plan_arbitration import arbitrate_goal_plan
from orchestration.runtime.rc3_introspection_engine import build_introspection_snapshot
from orchestration.runtime.rc3_plan_validator import PlanValidation, validate_plan
from orchestration.runtime.rc3_progress_evaluator import evaluate_progress

REPORT_JSON = ROOT / "reports" / "RC3_B_PLAN_REVISION.json"
REPORT_MD = ROOT / "reports" / "RC3_B_PLAN_REVISION.md"
BENCHMARK_JSON = ROOT / "reports" / "RC3_B_REVISION_BENCHMARK.json"
BENCHMARK_MD = ROOT / "reports" / "RC3_B_REVISION_BENCHMARK.md"
MILESTONE_JSON = ROOT / "reports" / "RC3_B_MILESTONE_REVIEW.json"
MILESTONE_MD = ROOT / "reports" / "RC3_B_MILESTONE_REVIEW.md"


SUPPORTED_TRIGGERS = (
    "user_changes_objective",
    "clarification_received",
    "assumption_invalidated",
    "prerequisite_unavailable",
    "dependency_failure",
    "operator_correction",
    "evidence_update",
    "capability_change",
    "safety_restriction",
    "scope_reduction",
    "scope_expansion",
    "conflicting_goal",
    "higher_priority_goal",
)


@dataclass(frozen=True)
class PlanRevisionRequest:
    trigger: str
    updated_constraints: tuple[str, ...] = ()
    new_evidence: tuple[str, ...] = ()
    changed_assumptions: tuple[str, ...] = ()
    operator_clarification: str = ""
    operator_notes: str = ""
    requested_scope: str = "same_scope"


@dataclass(frozen=True)
class PlanRevisionReasoning:
    revision_cause: str
    evidence_used: tuple[str, ...]
    assumptions_changed: tuple[str, ...]
    constraints_affected: tuple[str, ...]
    risks_introduced: tuple[str, ...]
    risks_removed: tuple[str, ...]
    confidence: float
    uncertainty: str
    inspectable: bool = True


@dataclass(frozen=True)
class PlanDiff:
    added_steps: tuple[str, ...] = ()
    removed_steps: tuple[str, ...] = ()
    reordered_steps: tuple[str, ...] = ()
    modified_outputs: tuple[str, ...] = ()
    modified_dependencies: tuple[str, ...] = ()
    modified_validation: tuple[str, ...] = ()
    modified_assumptions: tuple[str, ...] = ()
    modified_permissions: tuple[str, ...] = ()
    human_readable: tuple[str, ...] = ()


@dataclass(frozen=True)
class RevisionHistoryEntry:
    revision_number: int
    timestamp: str
    trigger: str
    previous_plan_reference: str
    revised_plan_reference: str
    revision_summary: str
    operator_notes: str
    confidence: float
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class RevisionMonitoring:
    stale_plan: bool
    repeated_revisions: bool
    contradictory_revisions: bool
    oscillation: bool
    stagnation: bool
    missing_evidence: bool
    incomplete_goal: bool
    diagnostics: tuple[str, ...]
    observational_only: bool = True


@dataclass(frozen=True)
class RevisionSelfEvaluation:
    revision_quality: float
    consistency: float
    evidence_quality: float
    confidence: float
    uncertainty: str
    remaining_risks: tuple[str, ...]
    missing_information: tuple[str, ...]
    certainty_claimed: bool = False


@dataclass(frozen=True)
class ControlledForgettingHook:
    obsolete_assumptions: tuple[str, ...]
    superseded_revisions: tuple[str, ...]
    abandoned_plans: tuple[str, ...]
    archived_alternatives: tuple[str, ...]
    deletes_anything: bool = False
    persists_anything: bool = False


@dataclass(frozen=True)
class PlanRevisionResult:
    decision: str
    revision_applied: bool
    revised_plan: PlanFrame
    reasoning: PlanRevisionReasoning
    validation: PlanValidation
    diff: PlanDiff
    history: tuple[RevisionHistoryEntry, ...]
    monitoring: RevisionMonitoring
    self_evaluation: RevisionSelfEvaluation
    controlled_forgetting_hook: ControlledForgettingHook
    arbitration_status: str
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


def revise_plan(
    goal: GoalFrame,
    existing_plan: PlanFrame,
    request: PlanRevisionRequest,
    *,
    progress: ProgressEvaluation | None = None,
    capability_gap: CapabilityGapAssessment | None = None,
    prior_history: tuple[RevisionHistoryEntry, ...] = (),
) -> PlanRevisionResult:
    """Return a governed revision result for a plan."""

    if request.trigger not in SUPPORTED_TRIGGERS:
        return _no_revision_result(goal, existing_plan, request, prior_history, "unsupported_revision_trigger")
    if not _has_justification(request, progress, capability_gap):
        return _no_revision_result(goal, existing_plan, request, prior_history, "revision_request_has_no_justification")

    revised_plan = _build_revised_plan(goal, existing_plan, request)
    validation = validate_plan(goal, revised_plan)
    if validation.result in ("blocked", "rejected"):
        decision = "require_clarification" if validation.required_clarification else "abandon_revision"
        revision_applied = False
        final_plan = existing_plan
    else:
        decision = _decision_for_trigger(request.trigger)
        revision_applied = decision in ("revise_existing_plan", "replace_plan_entirely")
        final_plan = revised_plan

    diff = compare_plans(existing_plan, revised_plan)
    reasoning = _reasoning(request, diff, validation)
    history = prior_history + (
        RevisionHistoryEntry(
            revision_number=len(prior_history) + 1,
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            trigger=request.trigger,
            previous_plan_reference=existing_plan.plan_id,
            revised_plan_reference=revised_plan.plan_id,
            revision_summary=_summary(request, diff, validation),
            operator_notes=request.operator_notes,
            confidence=reasoning.confidence,
        ),
    )
    monitoring = monitor_revisions(history, progress=progress)
    self_eval = evaluate_revision_quality(diff, validation, reasoning, monitoring)
    hook = ControlledForgettingHook(
        obsolete_assumptions=request.changed_assumptions if request.trigger == "assumption_invalidated" else (),
        superseded_revisions=(existing_plan.plan_id,) if revision_applied else (),
        abandoned_plans=(existing_plan.plan_id,) if decision == "replace_plan_entirely" else (),
        archived_alternatives=(existing_plan.plan_id,) if revision_applied else (),
    )
    return PlanRevisionResult(
        decision=decision,
        revision_applied=revision_applied,
        revised_plan=final_plan,
        reasoning=reasoning,
        validation=validation,
        diff=diff,
        history=history,
        monitoring=monitoring,
        self_evaluation=self_eval,
        controlled_forgetting_hook=hook,
        arbitration_status="accepted_read_only_revision" if revision_applied else decision,
    )


def compare_plans(previous: PlanFrame, revised: PlanFrame) -> PlanDiff:
    previous_steps = {step.step_id: step for step in previous.steps}
    revised_steps = {step.step_id: step for step in revised.steps}
    previous_summaries = {step.summary: step for step in previous.steps}
    revised_summaries = {step.summary: step for step in revised.steps}
    added = tuple(summary for summary in revised_summaries if summary not in previous_summaries)
    removed = tuple(summary for summary in previous_summaries if summary not in revised_summaries)
    modified_outputs = []
    modified_dependencies = []
    modified_validation = []
    for summary, revised_step in revised_summaries.items():
        previous_step = previous_summaries.get(summary)
        if not previous_step:
            continue
        if previous_step.expected_evidence != revised_step.expected_evidence:
            modified_outputs.append(summary)
        if previous_step.dependency_ids != revised_step.dependency_ids:
            modified_dependencies.append(summary)
        if previous_step.risk != revised_step.risk or previous_step.uncertainty != revised_step.uncertainty:
            modified_validation.append(summary)
    modified_assumptions = tuple(item for item in revised.assumptions if item not in previous.assumptions)
    modified_permissions = tuple(item for item in revised.prohibited_actions if item not in previous.prohibited_actions)
    human = []
    if added:
        human.append(f"Added {len(added)} step(s): " + "; ".join(added))
    if removed:
        human.append(f"Removed {len(removed)} step(s): " + "; ".join(removed))
    if modified_assumptions:
        human.append("Changed assumptions: " + "; ".join(modified_assumptions))
    if modified_permissions:
        human.append("Changed permissions/prohibitions: " + "; ".join(modified_permissions))
    if not human:
        human.append("No material plan changes detected.")
    return PlanDiff(
        added_steps=added,
        removed_steps=removed,
        reordered_steps=(),
        modified_outputs=tuple(modified_outputs),
        modified_dependencies=tuple(modified_dependencies),
        modified_validation=tuple(modified_validation),
        modified_assumptions=modified_assumptions,
        modified_permissions=modified_permissions,
        human_readable=tuple(human),
    )


def monitor_revisions(
    history: tuple[RevisionHistoryEntry, ...],
    *,
    progress: ProgressEvaluation | None = None,
) -> RevisionMonitoring:
    triggers = [item.trigger for item in history]
    repeated = len(triggers) != len(set((item.trigger, item.revision_summary) for item in history))
    contradictory = "scope_expansion" in triggers and "scope_reduction" in triggers
    oscillation = len(history) >= 4 and len(set(triggers[-4:])) <= 2
    missing_evidence = bool(progress and progress.missing_evidence)
    incomplete = bool(progress and progress.status not in ("completed_with_evidence",))
    diagnostics = []
    if repeated:
        diagnostics.append("repeated revision pattern observed")
    if contradictory:
        diagnostics.append("scope expansion and reduction both present")
    if oscillation:
        diagnostics.append("possible oscillation in recent revisions")
    if missing_evidence:
        diagnostics.append("progress evaluation still has missing evidence")
    if incomplete:
        diagnostics.append("goal is not complete")
    return RevisionMonitoring(
        stale_plan=False,
        repeated_revisions=repeated,
        contradictory_revisions=contradictory,
        oscillation=oscillation,
        stagnation=bool(progress and progress.status in ("not_started", "blocked")),
        missing_evidence=missing_evidence,
        incomplete_goal=incomplete,
        diagnostics=tuple(diagnostics),
    )


def evaluate_revision_quality(
    diff: PlanDiff,
    validation: PlanValidation,
    reasoning: PlanRevisionReasoning,
    monitoring: RevisionMonitoring,
) -> RevisionSelfEvaluation:
    validation_score = 1.0 if validation.result in ("valid", "valid_with_warnings") else 0.35
    diff_score = 1.0 if diff.added_steps or diff.modified_assumptions or diff.modified_permissions else 0.5
    monitoring_penalty = 0.15 if monitoring.oscillation or monitoring.contradictory_revisions else 0.0
    quality = round(max(0.0, min(1.0, (validation_score + diff_score + reasoning.confidence) / 3 - monitoring_penalty)), 4)
    missing = list(validation.required_clarification)
    if monitoring.missing_evidence:
        missing.append("progress evidence")
    return RevisionSelfEvaluation(
        revision_quality=quality,
        consistency=validation_score,
        evidence_quality=0.85 if reasoning.evidence_used else 0.45,
        confidence=round(min(reasoning.confidence, quality), 4),
        uncertainty=reasoning.uncertainty,
        remaining_risks=tuple(validation.warnings) + monitoring.diagnostics,
        missing_information=tuple(dict.fromkeys(missing)),
    )


def build_rc3_revision_episode(
    user_message: str,
    request: PlanRevisionRequest,
    *,
    previous_episode: RC3Episode | None = None,
) -> RC3Episode:
    base = previous_episode or build_rc3_goal_planning_episode(user_message)
    gap = analyze_capability_gap(base.goal_frame, base.plan_frame)
    revision = revise_plan(
        base.goal_frame,
        base.plan_frame,
        request,
        progress=base.progress,
        capability_gap=gap,
        prior_history=tuple(
            RevisionHistoryEntry(**item)
            for item in base.developer_overlay.get("revision_history", ())
        ),
    )
    final_plan = revision.revised_plan
    validation = validate_plan(base.goal_frame, final_plan)
    arbitration = arbitrate_goal_plan(base.goal_frame, final_plan, validation)
    introspection = build_introspection_snapshot(base.goal_frame, final_plan, validation, arbitration)
    progress = evaluate_progress(base.goal_frame, final_plan, validation)
    final_gap = analyze_capability_gap(base.goal_frame, final_plan)
    overlay = dict(base.developer_overlay)
    overlay.update({
        "entry_point": "build_rc3_revision_episode",
        "revision_trace": asdict(revision),
        "revision_history": tuple(asdict(item) for item in revision.history),
        "revision_diff": asdict(revision.diff),
        "revision_monitoring": asdict(revision.monitoring),
        "revision_self_evaluation": asdict(revision.self_evaluation),
        "controlled_forgetting_hook": asdict(revision.controlled_forgetting_hook),
        "execution_authorized": False,
        "persistence_status": "ephemeral",
        "safety": dict(SAFETY_DEFAULTS),
    })
    return replace(
        base,
        episode_id=_stable_id("revision-episode", base.episode_id, request.trigger, final_plan.plan_id),
        plan_frame=final_plan,
        arbitration=arbitration,
        introspection=introspection,
        progress=progress,
        capability_gap=final_gap,
        developer_overlay=overlay,
        safety=dict(SAFETY_DEFAULTS),
    )


def render_revision_summary(episode: RC3Episode) -> dict[str, object]:
    base = render_rc3_foundation_summary(episode)
    trace = episode.developer_overlay.get("revision_trace") or {}
    diff = trace.get("diff") or {}
    decision = trace.get("decision", "no_revision")
    lines = [
        str(base["summary"]),
        f"Revision decision: {decision}.",
        "Revision diff: " + "; ".join(diff.get("human_readable", ("No material plan changes detected.",))),
        "Revision remains read-only and requires operator review before any future action-adjacent step.",
    ]
    return {
        "summary": " ".join(lines),
        "developer_overlay": episode.developer_overlay,
        "safety": episode.safety,
    }


def build_rc3_b_revision_report(write_reports: bool = True) -> dict[str, Any]:
    base = build_rc3_goal_planning_episode("Design an RC3 plugin interface, but do not implement or activate plugins.")
    request = PlanRevisionRequest(
        trigger="operator_correction",
        updated_constraints=("operator review required",),
        new_evidence=("operator clarified that only schema documentation is in scope",),
        changed_assumptions=("implementation is deferred",),
        operator_notes="Keep this as a design-only revision.",
        requested_scope="scope_reduction",
    )
    revised = build_rc3_revision_episode(base.source_text, request, previous_episode=base)
    trace = revised.developer_overlay["revision_trace"]
    report = {
        "report": "RC3_B_PLAN_REVISION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "episode": revised.to_dict(),
        "revision_decision": trace["decision"],
        "revision_applied": trace["revision_applied"],
        "history_count": len(trace["history"]),
        "monitoring": trace["monitoring"],
        "self_evaluation": trace["self_evaluation"],
        "controlled_forgetting_hook": trace["controlled_forgetting_hook"],
        "safety": dict(SAFETY_DEFAULTS),
        "recommendation": "READY_FOR_RC3_B_REVISION_BENCHMARK",
    }
    if write_reports:
        _write_revision_report(report)
    return report


def _has_justification(
    request: PlanRevisionRequest,
    progress: ProgressEvaluation | None,
    capability_gap: CapabilityGapAssessment | None,
) -> bool:
    progress_justifies = bool(progress and (progress.blockers or progress.failure_signals)) and request.trigger in (
        "dependency_failure",
        "prerequisite_unavailable",
        "safety_restriction",
        "evidence_update",
    )
    capability_justifies = bool(capability_gap and capability_gap.missing_capabilities) and request.trigger in (
        "capability_change",
        "prerequisite_unavailable",
    )
    return bool(
        request.updated_constraints
        or request.new_evidence
        or request.changed_assumptions
        or request.operator_clarification
        or request.operator_notes
        or progress_justifies
        or capability_justifies
    )


def _build_revised_plan(goal: GoalFrame, existing: PlanFrame, request: PlanRevisionRequest) -> PlanFrame:
    extra_steps: list[PlanStepFrame] = []
    if request.operator_clarification:
        extra_steps.append(_step(goal, "Incorporate operator clarification before further review.", ("operator_clarification",)))
    if request.new_evidence:
        extra_steps.append(_step(goal, "Review new evidence and update validation expectations.", ("evidence_review",)))
    if request.updated_constraints:
        extra_steps.append(_step(goal, "Verify the revised plan preserves updated constraints.", ("constraint_review",)))
    if request.trigger in ("scope_reduction", "safety_restriction"):
        extra_steps.append(_step(goal, "Remove or defer steps outside the revised safe scope.", ("scope_review",)))
    if not extra_steps:
        extra_steps.append(_step(goal, "Record revision rationale for operator review.", ("revision_trace",)))
    revised_constraints = tuple(dict.fromkeys(existing.constraints_preserved + request.updated_constraints))
    revised_assumptions = tuple(dict.fromkeys(existing.assumptions + request.changed_assumptions))
    return PlanFrame(
        plan_id=_stable_id("revised-plan", existing.plan_id, request.trigger, "|".join(request.new_evidence), "|".join(request.updated_constraints)),
        goal_id=existing.goal_id,
        strategy=existing.strategy,
        lifecycle_state="reviewable_revision",
        steps=existing.steps + tuple(extra_steps),
        constraints_preserved=revised_constraints,
        dependencies=existing.dependencies + tuple(step.step_id for step in extra_steps),
        risks=tuple(dict.fromkeys(existing.risks + _revision_risks(request))),
        assumptions=revised_assumptions,
        prohibited_actions=existing.prohibited_actions,
        execution_authorized=False,
        persistence_status="ephemeral",
        provenance={**existing.provenance, "revision_trigger": request.trigger, "revision_engine": "rc3_plan_revision"},
        confidence=min(0.9, existing.confidence + 0.03),
        uncertainty="moderate",
        safety=dict(SAFETY_DEFAULTS),
    )


def _step(goal: GoalFrame, summary: str, evidence: tuple[str, ...]) -> PlanStepFrame:
    return PlanStepFrame(
        step_id=_stable_id("revision-step", goal.goal_id, summary),
        summary=summary,
        dependency_ids=(),
        preserves_constraints=goal.constraints,
        prohibited_actions=goal.prohibited_actions,
        expected_evidence=evidence,
        risk="low",
        uncertainty="moderate",
        non_executing=True,
    )


def _revision_risks(request: PlanRevisionRequest) -> tuple[str, ...]:
    risks = ["Revision may drift from the original plan if operator review is skipped."]
    if request.requested_scope == "scope_expansion":
        risks.append("Scope expansion may introduce unreviewed work.")
    if request.trigger == "conflicting_goal":
        risks.append("Conflicting goal may require clarification.")
    return tuple(risks)


def _decision_for_trigger(trigger: str) -> str:
    if trigger in ("user_changes_objective", "conflicting_goal", "higher_priority_goal"):
        return "replace_plan_entirely"
    if trigger in ("operator_correction", "clarification_received", "evidence_update", "assumption_invalidated", "safety_restriction", "scope_reduction", "scope_expansion", "capability_change", "dependency_failure", "prerequisite_unavailable"):
        return "revise_existing_plan"
    return "continue_current_plan"


def _reasoning(request: PlanRevisionRequest, diff: PlanDiff, validation: PlanValidation) -> PlanRevisionReasoning:
    confidence = 0.86 if validation.result in ("valid", "valid_with_warnings") else 0.42
    uncertainty = "moderate" if confidence >= 0.75 else "high"
    return PlanRevisionReasoning(
        revision_cause=request.trigger,
        evidence_used=request.new_evidence,
        assumptions_changed=request.changed_assumptions,
        constraints_affected=request.updated_constraints,
        risks_introduced=("scope drift",) if request.requested_scope == "scope_expansion" else (),
        risks_removed=("unsafe scope reduced",) if request.requested_scope == "scope_reduction" else (),
        confidence=confidence,
        uncertainty=uncertainty,
    )


def _summary(request: PlanRevisionRequest, diff: PlanDiff, validation: PlanValidation) -> str:
    return f"{request.trigger}: {validation.result}; " + " ".join(diff.human_readable)


def _no_revision_result(
    goal: GoalFrame,
    existing_plan: PlanFrame,
    request: PlanRevisionRequest,
    prior_history: tuple[RevisionHistoryEntry, ...],
    reason: str,
) -> PlanRevisionResult:
    validation = validate_plan(goal, existing_plan)
    reasoning = PlanRevisionReasoning(
        revision_cause=request.trigger,
        evidence_used=request.new_evidence,
        assumptions_changed=request.changed_assumptions,
        constraints_affected=request.updated_constraints,
        risks_introduced=(),
        risks_removed=(),
        confidence=0.2,
        uncertainty=reason,
    )
    diff = compare_plans(existing_plan, existing_plan)
    monitoring = monitor_revisions(prior_history)
    self_eval = evaluate_revision_quality(diff, validation, reasoning, monitoring)
    hook = ControlledForgettingHook((), (), (), ())
    return PlanRevisionResult(
        decision="continue_current_plan" if reason == "revision_request_has_no_justification" else "require_clarification",
        revision_applied=False,
        revised_plan=existing_plan,
        reasoning=reasoning,
        validation=validation,
        diff=diff,
        history=prior_history,
        monitoring=monitoring,
        self_evaluation=self_eval,
        controlled_forgetting_hook=hook,
        arbitration_status=reason,
    )


def _write_revision_report(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3-B Plan Revision",
        "",
        f"Created: {report['created_at']}",
        f"Revision decision: {report['revision_decision']}",
        f"Revision applied: {report['revision_applied']}",
        f"History count: {report['history_count']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Safety",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["safety"].items())
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_rc3_b_revision_report(write_reports=True)
    print(json.dumps({
        "revision_decision": report["revision_decision"],
        "revision_applied": report["revision_applied"],
        "history_count": report["history_count"],
        "recommendation": report["recommendation"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
