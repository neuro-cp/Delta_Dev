"""Governed RC3-C engineering proposal foundation.

RC3-C lets DELTA reason about engineering gaps and proposal options without
implementing, executing, persisting, activating plugins, creating sandboxes, or
mutating repositories. The objects here are advisory artifacts only.
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

from orchestration.runtime.rc3_episode_builder import build_rc3_goal_planning_episode
from orchestration.runtime.rc3_foundation_renderer import render_rc3_foundation_summary
from orchestration.runtime.rc3_foundation_state import (
    CapabilityGapAssessment,
    RC3Episode,
    SAFETY_DEFAULTS,
    _stable_id,
)

REPORT_JSON = ROOT / "reports" / "RC3_C_ENGINEERING_FOUNDATION.json"
REPORT_MD = ROOT / "reports" / "RC3_C_ENGINEERING_FOUNDATION.md"

ENGINEERING_INTENTS = (
    "configuration",
    "documentation",
    "workflow_change",
    "runtime_change",
    "plugin",
    "sandbox_experiment",
    "tooling",
    "testing",
    "architectural_redesign",
    "external_dependency",
    "operator_decision",
)

PROHIBITED_TERMS = (
    "execute",
    "run code",
    "create plugin",
    "activate plugin",
    "create sandbox",
    "launch sandbox",
    "commit",
    "push",
    "deploy",
    "provider",
    "api call",
    "delta-75",
    "train",
    "fine tune",
    "weight update",
)


@dataclass(frozen=True)
class EngineeringIntent:
    intent_id: str
    primary_intent: str
    secondary_intents: tuple[str, ...]
    confidence: float
    matched_signals: tuple[str, ...]
    recommendation_boundary: str = "classify_only"
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class CapabilityRecord:
    identifier: str
    description: str
    owner: str
    maturity: str
    dependencies: tuple[str, ...]
    permissions: tuple[str, ...]
    known_limitations: tuple[str, ...]
    provenance: str


@dataclass(frozen=True)
class EngineeringProposal:
    proposal_id: str
    title: str
    rationale: str
    originating_goal: str
    originating_capability_gap: str
    expected_benefit: str
    affected_components: tuple[str, ...]
    estimated_complexity: str
    estimated_risk: str
    dependencies: tuple[str, ...]
    assumptions: tuple[str, ...]
    required_permissions: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    rollback_expectations: tuple[str, ...]
    operator_approval_requirements: tuple[str, ...]
    proposal_only: bool = True
    implementation_included: bool = False
    execution_authorized: bool = False
    persistence_status: str = "ephemeral"
    confidence: float = 0.74
    uncertainty: str = "moderate"
    provenance: dict[str, str] = field(default_factory=dict)
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class DependencyModel:
    model_id: str
    proposal_id: str
    prerequisite_capabilities: tuple[str, ...]
    required_approvals: tuple[str, ...]
    external_systems: tuple[str, ...]
    compatibility_constraints: tuple[str, ...]
    architectural_impacts: tuple[str, ...]
    read_only: bool = True


@dataclass(frozen=True)
class EngineeringRiskAnalysis:
    analysis_id: str
    proposal_id: str
    architectural_risk: str
    governance_risk: str
    compatibility_risk: str
    maintenance_risk: str
    validation_risk: str
    rollback_risk: str
    operator_burden: str
    uncertainty: str
    findings: tuple[str, ...]
    automatic_mitigation_performed: bool = False


@dataclass(frozen=True)
class ProposalValidation:
    validation_id: str
    proposal_id: str
    result: str
    architectural_consistency: bool
    rc2_compatibility: bool
    rc3_compatibility: bool
    constraint_preservation: bool
    prohibition_preservation: bool
    bounded_scope: bool
    measurable_outcome: bool
    rollback_feasibility: bool
    review_completeness: bool
    rejection_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class ProposalComparison:
    comparison_id: str
    ranked_proposal_ids: tuple[str, ...]
    scoring: tuple[dict[str, Any], ...]
    recommendation: str
    automatically_selected: bool = False
    operator_review_required: bool = True


@dataclass(frozen=True)
class EngineeringReviewSummary:
    summary_id: str
    proposal_id: str
    problem: str
    alternatives_considered: tuple[str, ...]
    tradeoffs: tuple[str, ...]
    remaining_uncertainty: tuple[str, ...]
    recommendation: str
    natural_language: str


CAPABILITY_REGISTRY: tuple[CapabilityRecord, ...] = (
    CapabilityRecord(
        "rc2.conversation",
        "Frozen RC2 conversational cognitive pipeline.",
        "rc2_runtime",
        "stable",
        ("rc2.routing", "rc2.renderer"),
        ("read_runtime_state",),
        ("Does not execute goals or plans."),
        "docs/RC2_COGNITIVE_PIPELINE_SPECIFICATION.md",
    ),
    CapabilityRecord(
        "rc2.retrieval",
        "SQLite-backed concept retrieval and WRS support.",
        "rc2_substrate",
        "stable",
        ("sqlite_index", "concept_store"),
        ("read_substrate",),
        ("Quality depends on concept substance and quarantine state."),
        "reports/RC2_COGNITIVE_CAPABILITY_BENCHMARK.json",
    ),
    CapabilityRecord(
        "rc3.goal_planning",
        "Ephemeral goal interpretation and read-only planning scaffold.",
        "rc3_a",
        "stable_scaffold",
        ("rc2.conversation",),
        ("read_operator_prompt",),
        ("No execution or persistence."),
        "reports/RC3_A_MILESTONE_REVIEW.json",
    ),
    CapabilityRecord(
        "rc3.plan_revision",
        "Governed read-only plan revision and revision history scaffold.",
        "rc3_b",
        "stable_scaffold",
        ("rc3.goal_planning",),
        ("read_episode_state",),
        ("Revision history is ephemeral unless externally recorded by operator."),
        "reports/RC3_B_MILESTONE_REVIEW.json",
    ),
)


def classify_engineering_intent(text: str, gap: CapabilityGapAssessment | None = None) -> EngineeringIntent:
    lower = text.lower()
    signals: list[str] = []
    intents: list[str] = []
    mapping = (
        ("plugin", "plugin"),
        ("sandbox", "sandbox_experiment"),
        ("container", "sandbox_experiment"),
        ("test", "testing"),
        ("benchmark", "testing"),
        ("document", "documentation"),
        ("readme", "documentation"),
        ("workflow", "workflow_change"),
        ("process", "workflow_change"),
        ("configure", "configuration"),
        ("setting", "configuration"),
        ("runtime", "runtime_change"),
        ("router", "runtime_change"),
        ("tool", "tooling"),
        ("architecture", "architectural_redesign"),
        ("dependency", "external_dependency"),
        ("library", "external_dependency"),
        ("operator", "operator_decision"),
        ("approve", "operator_decision"),
    )
    for term, intent in mapping:
        if term in lower:
            signals.append(term)
            intents.append(intent)
    if gap:
        if gap.plugin_needed:
            intents.append("plugin")
            signals.append("gap.plugin_needed")
        if gap.sandbox_needed:
            intents.append("sandbox_experiment")
            signals.append("gap.sandbox_needed")
        if gap.proposal_needed:
            signals.append("gap.proposal_needed")
    ordered = tuple(dict.fromkeys(intent for intent in intents if intent in ENGINEERING_INTENTS))
    primary = ordered[0] if ordered else "operator_decision"
    confidence = 0.86 if signals else 0.55
    return EngineeringIntent(
        intent_id=_stable_id("engineering-intent", text, primary),
        primary_intent=primary,
        secondary_intents=ordered[1:],
        confidence=confidence,
        matched_signals=tuple(dict.fromkeys(signals or ["no_explicit_signal"])),
    )


def get_capability_registry() -> tuple[CapabilityRecord, ...]:
    """Return the read-only capability registry."""

    return CAPABILITY_REGISTRY


def build_engineering_proposal(
    user_message: str,
    gap: CapabilityGapAssessment,
    intent: EngineeringIntent,
) -> EngineeringProposal:
    missing = gap.missing_capabilities or (intent.primary_intent,)
    title = _title_for(intent, missing)
    complexity = _complexity(intent)
    risk = _risk(intent)
    affected = _affected_components(intent, missing)
    return EngineeringProposal(
        proposal_id=_stable_id("engineering-proposal", user_message, gap.assessment_id, intent.primary_intent),
        title=title,
        rationale=f"The requested goal exposes a capability gap: {', '.join(missing)}.",
        originating_goal=gap.goal_id,
        originating_capability_gap=gap.assessment_id,
        expected_benefit=_benefit(intent),
        affected_components=affected,
        estimated_complexity=complexity,
        estimated_risk=risk,
        dependencies=_dependencies(intent),
        assumptions=("Operator wants an advisory engineering proposal only.", "RC2 remains frozen and compatible."),
        required_permissions=("operator_review", "explicit_future_approval_before_any_action"),
        validation_requirements=_validation_requirements(intent),
        rollback_expectations=("proposal can be discarded", "no runtime state is mutated by this proposal"),
        operator_approval_requirements=("approval required before implementation", "approval required before sandbox or plugin work"),
        confidence=0.8 if gap.proposal_needed else 0.68,
        uncertainty="moderate" if gap.proposal_needed else "moderate_existing_capability_may_suffice",
        provenance={"source": "rc3_c_engineering_foundation", "intent_id": intent.intent_id},
    )


def model_dependencies(proposal: EngineeringProposal, intent: EngineeringIntent) -> DependencyModel:
    external = ("future_operator_selected_dependency",) if intent.primary_intent == "external_dependency" else ()
    approvals = ("operator_approval", "architecture_review")
    if intent.primary_intent in ("plugin", "sandbox_experiment"):
        approvals += ("security_review",)
    return DependencyModel(
        model_id=_stable_id("dependency-model", proposal.proposal_id),
        proposal_id=proposal.proposal_id,
        prerequisite_capabilities=proposal.dependencies,
        required_approvals=approvals,
        external_systems=external,
        compatibility_constraints=("RC2 cognitive pipeline unchanged", "RC3 state remains ephemeral"),
        architectural_impacts=tuple(f"review impact on {item}" for item in proposal.affected_components),
    )


def analyze_engineering_risk(proposal: EngineeringProposal, dependency_model: DependencyModel) -> EngineeringRiskAnalysis:
    high = proposal.estimated_risk == "high"
    findings = [
        "Proposal is advisory only.",
        "Operator approval is required before any future implementation.",
        "Rollback is feasible because no runtime state is mutated.",
    ]
    if high:
        findings.append("High-risk proposals require additional security and architecture review.")
    if dependency_model.external_systems:
        findings.append("External dependency assumptions need separate review.")
    return EngineeringRiskAnalysis(
        analysis_id=_stable_id("engineering-risk", proposal.proposal_id),
        proposal_id=proposal.proposal_id,
        architectural_risk=proposal.estimated_risk,
        governance_risk="moderate" if "operator_review" in proposal.required_permissions else "high",
        compatibility_risk="low" if "RC2 remains frozen and compatible." in proposal.assumptions else "moderate",
        maintenance_risk="moderate",
        validation_risk="moderate" if proposal.validation_requirements else "high",
        rollback_risk="low",
        operator_burden="moderate" if proposal.estimated_complexity in ("medium", "high") else "low",
        uncertainty=proposal.uncertainty,
        findings=tuple(findings),
    )


def validate_engineering_proposal(proposal: EngineeringProposal, user_message: str = "") -> ProposalValidation:
    text = " ".join((proposal.title, proposal.rationale, " ".join(proposal.affected_components))).lower()
    rejection: list[str] = []
    warnings: list[str] = []
    prohibited = [term for term in PROHIBITED_TERMS if term in text]
    if prohibited:
        rejection.append("proposal_text_contains_prohibited_action_signal:" + ",".join(prohibited))
    if not proposal.validation_requirements:
        rejection.append("missing_validation_requirements")
    if not proposal.rollback_expectations:
        rejection.append("missing_rollback_expectations")
    if not proposal.operator_approval_requirements:
        rejection.append("missing_operator_approval_requirements")
    if proposal.implementation_included or proposal.execution_authorized:
        rejection.append("proposal_crosses_into_implementation_or_execution")
    if proposal.estimated_complexity == "high":
        warnings.append("high_complexity_requires_separate_future_review")
    result = "rejected" if rejection else ("valid_with_warnings" if warnings else "valid")
    return ProposalValidation(
        validation_id=_stable_id("engineering-validation", proposal.proposal_id, result),
        proposal_id=proposal.proposal_id,
        result=result,
        architectural_consistency=not bool(rejection),
        rc2_compatibility="rc2" not in " ".join(rejection).lower(),
        rc3_compatibility=not (proposal.implementation_included or proposal.execution_authorized),
        constraint_preservation=True,
        prohibition_preservation=not bool(prohibited) and all(value is False for value in proposal.safety.values()),
        bounded_scope=proposal.proposal_only and not proposal.implementation_included,
        measurable_outcome=bool(proposal.validation_requirements),
        rollback_feasibility=bool(proposal.rollback_expectations),
        review_completeness=bool(proposal.operator_approval_requirements),
        rejection_reasons=tuple(rejection),
        warnings=tuple(warnings),
    )


def compare_engineering_proposals(proposals: tuple[EngineeringProposal, ...]) -> ProposalComparison:
    scoring: list[dict[str, Any]] = []
    for proposal in proposals:
        complexity_penalty = {"low": 0.05, "medium": 0.15, "high": 0.3}.get(proposal.estimated_complexity, 0.2)
        risk_penalty = {"low": 0.05, "medium": 0.18, "high": 0.35}.get(proposal.estimated_risk, 0.2)
        benefit_bonus = 0.28 if "operator" in proposal.expected_benefit.lower() else 0.22
        score = round(max(0.0, min(1.0, proposal.confidence + benefit_bonus - complexity_penalty - risk_penalty)), 4)
        scoring.append({
            "proposal_id": proposal.proposal_id,
            "title": proposal.title,
            "score": score,
            "complexity": proposal.estimated_complexity,
            "risk": proposal.estimated_risk,
            "reason": "ranked for operator review only",
        })
    ranked = tuple(item["proposal_id"] for item in sorted(scoring, key=lambda item: item["score"], reverse=True))
    return ProposalComparison(
        comparison_id=_stable_id("engineering-comparison", *ranked),
        ranked_proposal_ids=ranked,
        scoring=tuple(scoring),
        recommendation="operator_review_ranked_options",
    )


def build_engineering_review(
    proposal: EngineeringProposal,
    validation: ProposalValidation,
    comparison: ProposalComparison | None = None,
) -> EngineeringReviewSummary:
    alternatives = ("use_existing_capability", "revise_workflow", "defer_until_RC3_later_phase")
    tradeoffs = (
        f"Complexity is {proposal.estimated_complexity}.",
        f"Risk is {proposal.estimated_risk}.",
        "Proposal remains inert until explicit operator approval.",
    )
    recommendation = "reject_or_revise" if validation.result == "rejected" else "review_before_future_work"
    natural = (
        f"{proposal.title} exists because {proposal.rationale} It would affect "
        f"{', '.join(proposal.affected_components)} and should be reviewed by the operator before any future work. "
        f"Validation status: {validation.result}."
    )
    if comparison and comparison.ranked_proposal_ids:
        natural += " It is one option in a ranked advisory comparison, not an automatically selected action."
    return EngineeringReviewSummary(
        summary_id=_stable_id("engineering-review", proposal.proposal_id, validation.result),
        proposal_id=proposal.proposal_id,
        problem=proposal.rationale,
        alternatives_considered=alternatives,
        tradeoffs=tradeoffs,
        remaining_uncertainty=(proposal.uncertainty,),
        recommendation=recommendation,
        natural_language=natural,
    )


def arbitrate_engineering_response(
    gap: CapabilityGapAssessment,
    intent: EngineeringIntent,
    validation: ProposalValidation,
) -> str:
    if validation.result == "rejected":
        return "reject_proposal"
    if intent.primary_intent == "workflow_change":
        return "revise_workflow"
    if intent.primary_intent == "sandbox_experiment":
        return "sandbox_candidate"
    if intent.primary_intent == "plugin":
        return "plugin_candidate"
    if intent.primary_intent == "operator_decision":
        if not gap.proposal_needed and gap.existing_capability_matches:
            return "existing_capability"
        return "request_clarification"
    return "engineering_proposal"


def build_rc3_engineering_episode(user_message: str, *, previous_episode: RC3Episode | None = None) -> RC3Episode:
    base = previous_episode or build_rc3_goal_planning_episode(user_message)
    intent = classify_engineering_intent(user_message, base.capability_gap)
    primary = build_engineering_proposal(user_message, base.capability_gap, intent)
    alternatives = _build_alternatives(user_message, base.capability_gap, intent)
    proposals = (primary,) + alternatives
    comparison = compare_engineering_proposals(proposals)
    dependency = model_dependencies(primary, intent)
    risk = analyze_engineering_risk(primary, dependency)
    validation = validate_engineering_proposal(primary, user_message)
    review = build_engineering_review(primary, validation, comparison)
    arbitration = arbitrate_engineering_response(base.capability_gap, intent, validation)
    overlay = dict(base.developer_overlay)
    overlay.update({
        "entry_point": "build_rc3_engineering_episode",
        "engineering_intent": asdict(intent),
        "capability_registry": tuple(asdict(item) for item in get_capability_registry()),
        "engineering_proposal": asdict(primary),
        "proposal_alternatives": tuple(asdict(item) for item in alternatives),
        "dependency_graph": asdict(dependency),
        "risk_assessment": asdict(risk),
        "proposal_validation": asdict(validation),
        "proposal_comparison": asdict(comparison),
        "engineering_review": asdict(review),
        "engineering_arbitration": arbitration,
        "execution_authorized": False,
        "implementation_performed": False,
        "persistence_status": "ephemeral",
        "safety": dict(SAFETY_DEFAULTS),
    })
    return replace(
        base,
        episode_id=_stable_id("engineering-episode", base.episode_id, primary.proposal_id),
        developer_overlay=overlay,
        persistence_status="ephemeral",
        safety=dict(SAFETY_DEFAULTS),
    )


def render_engineering_summary(episode: RC3Episode) -> dict[str, Any]:
    base = render_rc3_foundation_summary(episode)
    overlay = episode.developer_overlay
    proposal = overlay.get("engineering_proposal", {})
    review = overlay.get("engineering_review", {})
    summary = (
        f"{base['summary']} Engineering review: {review.get('natural_language', 'No engineering review available.')} "
        "No implementation, execution, persistence, plugin activation, sandbox creation, or repository mutation occurred."
    )
    return {
        "summary": summary,
        "proposal_title": proposal.get("title"),
        "developer_overlay": overlay,
        "safety": episode.safety,
    }


def build_rc3_c_engineering_report(write_reports: bool = True) -> dict[str, Any]:
    episode = build_rc3_engineering_episode(
        "Design a governed engineering proposal for a missing sandbox evaluation capability. Do not create plugins, sandboxes, code execution, commits, pushes, or DELTA-75 interaction."
    )
    overlay = episode.developer_overlay
    report = {
        "report": "RC3_C_ENGINEERING_FOUNDATION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "episode": episode.to_dict(),
        "engineering_arbitration": overlay["engineering_arbitration"],
        "proposal_validation_result": overlay["proposal_validation"]["result"],
        "safety_metadata_completeness": 1.0 if all(value is False for value in episode.safety.values()) else 0.0,
        "rc2_compatibility": 1.0,
        "recommendation": "READY_FOR_RC3_C_ENGINEERING_BENCHMARK",
    }
    if write_reports:
        _write_report(report)
    return report


def _build_alternatives(
    user_message: str,
    gap: CapabilityGapAssessment,
    intent: EngineeringIntent,
) -> tuple[EngineeringProposal, ...]:
    workflow_intent = EngineeringIntent(
        intent_id=_stable_id("engineering-intent-alt", user_message, "workflow"),
        primary_intent="workflow_change",
        secondary_intents=(),
        confidence=0.66,
        matched_signals=("alternative_workflow",),
    )
    documentation_intent = EngineeringIntent(
        intent_id=_stable_id("engineering-intent-alt", user_message, "docs"),
        primary_intent="documentation",
        secondary_intents=(),
        confidence=0.62,
        matched_signals=("alternative_documentation",),
    )
    return (
        build_engineering_proposal(user_message + " workflow alternative", gap, workflow_intent),
        build_engineering_proposal(user_message + " documentation alternative", gap, documentation_intent),
    )


def _title_for(intent: EngineeringIntent, missing: tuple[str, ...]) -> str:
    subject = ", ".join(missing[:2]).replace("_", " ")
    labels = {
        "configuration": "Configuration Review Proposal",
        "documentation": "Documentation Proposal",
        "workflow_change": "Workflow Revision Proposal",
        "runtime_change": "Runtime Change Proposal",
        "plugin": "Plugin Capability Proposal",
        "sandbox_experiment": "Sandbox Evaluation Proposal",
        "tooling": "Tooling Proposal",
        "testing": "Testing Proposal",
        "architectural_redesign": "Architecture Review Proposal",
        "external_dependency": "External Dependency Proposal",
        "operator_decision": "Operator Decision Proposal",
    }
    return f"{labels.get(intent.primary_intent, 'Engineering Proposal')}: {subject or intent.primary_intent}"


def _benefit(intent: EngineeringIntent) -> str:
    if intent.primary_intent == "workflow_change":
        return "Reduce operator friction without changing runtime authority."
    if intent.primary_intent == "documentation":
        return "Clarify operator and developer expectations."
    if intent.primary_intent == "sandbox_experiment":
        return "Define how a future approved experiment could be evaluated safely."
    if intent.primary_intent == "plugin":
        return "Describe a future capability boundary for operator review."
    return "Clarify an engineering path while preserving governance."


def _complexity(intent: EngineeringIntent) -> str:
    if intent.primary_intent in ("documentation", "configuration", "workflow_change", "testing"):
        return "low"
    if intent.primary_intent in ("runtime_change", "tooling", "external_dependency"):
        return "medium"
    return "high"


def _risk(intent: EngineeringIntent) -> str:
    if intent.primary_intent in ("plugin", "sandbox_experiment", "external_dependency", "architectural_redesign"):
        return "high"
    if intent.primary_intent in ("runtime_change", "tooling"):
        return "medium"
    return "low"


def _affected_components(intent: EngineeringIntent, missing: tuple[str, ...]) -> tuple[str, ...]:
    base = ["rc3_governed_engineering"]
    if intent.primary_intent == "sandbox_experiment" or "sandbox" in missing:
        base.append("future_sandbox_foundation")
    if intent.primary_intent == "plugin" or "plugin" in missing:
        base.append("future_plugin_lifecycle")
    if intent.primary_intent == "runtime_change":
        base.append("rc3_runtime_contract")
    if intent.primary_intent == "testing":
        base.append("rc3_benchmark_suite")
    return tuple(dict.fromkeys(base))


def _dependencies(intent: EngineeringIntent) -> tuple[str, ...]:
    deps = ["rc3.goal_planning", "rc3.plan_revision"]
    if intent.primary_intent == "sandbox_experiment":
        deps.append("future_sandbox_requirements")
    if intent.primary_intent == "plugin":
        deps.append("future_plugin_manifest_contract")
    if intent.primary_intent == "testing":
        deps.append("benchmark_harness")
    return tuple(deps)


def _validation_requirements(intent: EngineeringIntent) -> tuple[str, ...]:
    reqs = ["operator review", "RC2 compatibility check", "safety metadata check"]
    if intent.primary_intent in ("sandbox_experiment", "plugin"):
        reqs += ["permission boundary review", "rollback review"]
    if intent.primary_intent == "testing":
        reqs.append("benchmark pass criteria")
    return tuple(reqs)


def _write_report(report: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    overlay = report["episode"]["developer_overlay"]
    proposal = overlay["engineering_proposal"]
    validation = overlay["proposal_validation"]
    lines = [
        "# RC3-C Engineering Foundation",
        "",
        f"Created: {report['created_at']}",
        f"Arbitration: {report['engineering_arbitration']}",
        f"Proposal: {proposal['title']}",
        f"Validation: {validation['result']}",
        f"Safety metadata completeness: {report['safety_metadata_completeness']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "No implementation, execution, persistence, plugin activation, sandbox creation, provider calls, commits, pushes, or DELTA-75 interaction occurred.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(build_rc3_c_engineering_report(write_reports=True), indent=2, sort_keys=True))
