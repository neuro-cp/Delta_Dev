"""Governed RC3-D sandbox foundation.

RC3-D models what safe evaluation environment a future approved engineering
proposal might require. It never creates a sandbox, container, VM, process,
plugin, filesystem mutation, provider call, network request, or execution.
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

from orchestration.runtime.rc3_engineering_foundation import (
    EngineeringProposal,
    ProposalValidation,
    build_rc3_engineering_episode,
    validate_engineering_proposal,
)
from orchestration.runtime.rc3_foundation_state import RC3Episode, SAFETY_DEFAULTS, _stable_id

REPORT_JSON = ROOT / "reports" / "RC3_D_SANDBOX_FOUNDATION.json"
REPORT_MD = ROOT / "reports" / "RC3_D_SANDBOX_FOUNDATION.md"

ISOLATION_LEVELS = (
    "documentation_only",
    "logical_isolation",
    "process_isolation",
    "container_isolation",
    "vm_isolation",
    "air_gapped_evaluation",
    "operator_only_handling",
)


@dataclass(frozen=True)
class SandboxRequirement:
    requirement_id: str
    recommendation: str
    required_capabilities: tuple[str, ...]
    isolation_classification: str
    justification: str
    confidence: float
    uncertainty: str
    no_environment_created: bool = True
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class ResourceEstimate:
    estimate_id: str
    cpu: str
    memory: str
    storage: str
    runtime_duration: str
    external_dependencies: tuple[str, ...]
    expected_outputs: tuple[str, ...]
    planning_estimate_only: bool = True


@dataclass(frozen=True)
class SandboxSpecification:
    specification_id: str
    filesystem_policy: str
    network_policy: str
    provider_policy: str
    memory_policy: str
    plugin_policy: str
    logging_policy: str
    persistence_policy: str
    destruction_policy: str
    provenance_policy: str
    runtime_implementation_included: bool = False


@dataclass(frozen=True)
class SandboxProposal:
    sandbox_proposal_id: str
    originating_proposal_id: str
    objective: str
    justification: str
    required_isolation_level: str
    required_resources: ResourceEstimate
    expected_duration: str
    expected_artifacts: tuple[str, ...]
    validation_goals: tuple[str, ...]
    success_criteria: tuple[str, ...]
    rollback_expectations: tuple[str, ...]
    destruction_policy: str
    operator_approval_requirements: tuple[str, ...]
    specification: SandboxSpecification
    proposal_only: bool = True
    sandbox_created: bool = False
    execution_authorized: bool = False
    persistence_status: str = "ephemeral"
    confidence: float = 0.76
    uncertainty: str = "moderate"
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class SandboxSafetyReview:
    review_id: str
    sandbox_proposal_id: str
    privilege_escalation_risk: str
    persistence_risk: str
    repository_mutation_risk: str
    provider_interaction_risk: str
    network_exposure_risk: str
    data_leakage_risk: str
    rollback_feasibility: str
    reproducibility: str
    auditability: str
    findings: tuple[str, ...]
    safety_margin: str


@dataclass(frozen=True)
class SandboxValidation:
    validation_id: str
    sandbox_proposal_id: str
    result: str
    complete_specification: bool
    bounded_scope: bool
    defined_entry_conditions: bool
    defined_exit_conditions: bool
    destruction_policy: bool
    rollback_policy: bool
    approval_requirements: bool
    architectural_consistency: bool
    rc2_compatibility: bool
    rc3_compatibility: bool
    rejection_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class SandboxComparison:
    comparison_id: str
    ranked_sandbox_proposal_ids: tuple[str, ...]
    scoring: tuple[dict[str, Any], ...]
    recommendation: str
    automatically_selected: bool = False
    operator_review_required: bool = True


@dataclass(frozen=True)
class SandboxReviewSummary:
    summary_id: str
    sandbox_proposal_id: str
    why_needed: str
    proposed_isolation_model: str
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    residual_risks: tuple[str, ...]
    operator_decisions_required: tuple[str, ...]
    natural_language: str


def analyze_sandbox_requirement(proposal: EngineeringProposal) -> SandboxRequirement:
    text = " ".join((proposal.title, proposal.rationale, " ".join(proposal.affected_components))).lower()
    required: list[str] = []
    if "sandbox" in text:
        required.append("isolated evaluation design")
    if "plugin" in text:
        required.append("isolated plugin environment")
    if "code" in text or "runtime" in text:
        required.append("isolated runtime")
    if "external" in text or "dependency" in text:
        required.append("isolated network review")
    if not required and proposal.estimated_risk == "low":
        recommendation = "documentation review"
        level = "documentation_only"
        confidence = 0.82
    elif proposal.estimated_risk == "high":
        recommendation = "sandbox design required before any future evaluation"
        level = "container_isolation" if "vm" not in text else "vm_isolation"
        confidence = 0.84
    else:
        recommendation = "logical isolation design sufficient for proposal review"
        level = "logical_isolation"
        confidence = 0.74
    return SandboxRequirement(
        requirement_id=_stable_id("sandbox-requirement", proposal.proposal_id, level),
        recommendation=recommendation,
        required_capabilities=tuple(dict.fromkeys(required or ["human-only review"])),
        isolation_classification=level,
        justification=f"Classified from proposal risk={proposal.estimated_risk}, complexity={proposal.estimated_complexity}.",
        confidence=confidence,
        uncertainty="moderate" if confidence < 0.8 else "low",
    )


def estimate_resources(requirement: SandboxRequirement) -> ResourceEstimate:
    level = requirement.isolation_classification
    if level in ("documentation_only", "logical_isolation"):
        cpu, memory, storage, duration = "none_or_operator_workstation", "none_or_small", "minimal", "minutes"
    elif level == "process_isolation":
        cpu, memory, storage, duration = "1-2 cores", "1-4 GB", "temporary workspace", "minutes_to_hours"
    elif level == "container_isolation":
        cpu, memory, storage, duration = "2-4 cores", "4-8 GB", "disposable container volume", "hours"
    else:
        cpu, memory, storage, duration = "dedicated host allocation", "8+ GB", "disposable image", "operator_defined"
    return ResourceEstimate(
        estimate_id=_stable_id("sandbox-resource", requirement.requirement_id),
        cpu=cpu,
        memory=memory,
        storage=storage,
        runtime_duration=duration,
        external_dependencies=("operator-approved dependency list",) if "network" in " ".join(requirement.required_capabilities) else (),
        expected_outputs=("validation report", "audit log", "operator review packet"),
    )


def build_sandbox_specification(requirement: SandboxRequirement) -> SandboxSpecification:
    network = "disabled_by_default"
    if requirement.isolation_classification in ("documentation_only", "logical_isolation"):
        network = "not_applicable_no_execution"
    elif "network" in " ".join(requirement.required_capabilities):
        network = "disabled_unless_operator_whitelists_specific_endpoint"
    return SandboxSpecification(
        specification_id=_stable_id("sandbox-spec", requirement.requirement_id),
        filesystem_policy="read-only inputs, disposable outputs, no production writes",
        network_policy=network,
        provider_policy="providers disabled unless separately consented for a single reviewed request",
        memory_policy="no hidden persistence; memory discarded after review packet generation",
        plugin_policy="plugins unavailable unless separately approved and isolated",
        logging_policy="audit logs required for every planned operation",
        persistence_policy="ephemeral by default; reviewed artifacts only",
        destruction_policy="destroy disposable workspace after operator-reviewed export",
        provenance_policy="record proposal id, source prompt, assumptions, and validation evidence",
    )


def build_sandbox_proposal(
    engineering_proposal: EngineeringProposal,
    requirement: SandboxRequirement,
) -> SandboxProposal:
    resources = estimate_resources(requirement)
    specification = build_sandbox_specification(requirement)
    return SandboxProposal(
        sandbox_proposal_id=_stable_id("sandbox-proposal", engineering_proposal.proposal_id, requirement.requirement_id),
        originating_proposal_id=engineering_proposal.proposal_id,
        objective=f"Define an inert sandbox requirement for {engineering_proposal.title}.",
        justification=requirement.justification,
        required_isolation_level=requirement.isolation_classification,
        required_resources=resources,
        expected_duration=resources.runtime_duration,
        expected_artifacts=("sandbox specification", "safety review", "validation checklist"),
        validation_goals=("prove isolation requirements are explicit", "prove no execution is authorized"),
        success_criteria=("operator can review the sandbox design", "all policies are complete", "destruction and rollback are defined"),
        rollback_expectations=("discard proposal", "no runtime state changed", "no sandbox exists to clean up"),
        destruction_policy=specification.destruction_policy,
        operator_approval_requirements=("approval required before any future sandbox creation", "approval required before any future execution"),
        specification=specification,
        confidence=requirement.confidence,
        uncertainty=requirement.uncertainty,
    )


def review_sandbox_safety(proposal: SandboxProposal) -> SandboxSafetyReview:
    high_isolation = proposal.required_isolation_level in ("container_isolation", "vm_isolation", "air_gapped_evaluation")
    findings = [
        "Sandbox proposal is design-only.",
        "No sandbox, process, container, VM, plugin, filesystem mutation, provider call, or execution was created.",
        "Operator approval is required before any future environment work.",
    ]
    if high_isolation:
        findings.append("High isolation has stronger safety margin but higher operational cost.")
    return SandboxSafetyReview(
        review_id=_stable_id("sandbox-safety", proposal.sandbox_proposal_id),
        sandbox_proposal_id=proposal.sandbox_proposal_id,
        privilege_escalation_risk="low_in_design_phase",
        persistence_risk="low_no_persistence",
        repository_mutation_risk="low_no_repository_mutation",
        provider_interaction_risk="low_providers_disabled",
        network_exposure_risk="low" if "disabled" in proposal.specification.network_policy else "moderate",
        data_leakage_risk="low_with_disposable_outputs",
        rollback_feasibility="high_no_runtime_state_changed",
        reproducibility="high_specification_is_structured",
        auditability="high_review_packet_available",
        findings=tuple(findings),
        safety_margin="strong" if high_isolation else "adequate",
    )


def validate_sandbox_proposal(proposal: SandboxProposal) -> SandboxValidation:
    rejection: list[str] = []
    warnings: list[str] = []
    spec = proposal.specification
    if proposal.sandbox_created or proposal.execution_authorized:
        rejection.append("sandbox_creation_or_execution_authorized")
    if not proposal.operator_approval_requirements:
        rejection.append("missing_operator_approval_requirements")
    if not proposal.rollback_expectations:
        rejection.append("missing_rollback_expectations")
    if spec.runtime_implementation_included:
        rejection.append("specification_includes_runtime_implementation")
    if proposal.required_isolation_level not in ISOLATION_LEVELS:
        rejection.append("unknown_isolation_level")
    if proposal.required_isolation_level == "documentation_only":
        warnings.append("documentation_only_isolation_not_sufficient_for_future_execution")
    result = "rejected" if rejection else ("valid_with_warnings" if warnings else "valid")
    return SandboxValidation(
        validation_id=_stable_id("sandbox-validation", proposal.sandbox_proposal_id, result),
        sandbox_proposal_id=proposal.sandbox_proposal_id,
        result=result,
        complete_specification=all(bool(getattr(spec, field_name)) for field_name in (
            "filesystem_policy",
            "network_policy",
            "provider_policy",
            "memory_policy",
            "plugin_policy",
            "logging_policy",
            "persistence_policy",
            "destruction_policy",
            "provenance_policy",
        )),
        bounded_scope=proposal.proposal_only and not proposal.sandbox_created,
        defined_entry_conditions=bool(proposal.validation_goals),
        defined_exit_conditions=bool(proposal.success_criteria),
        destruction_policy=bool(proposal.destruction_policy),
        rollback_policy=bool(proposal.rollback_expectations),
        approval_requirements=bool(proposal.operator_approval_requirements),
        architectural_consistency=not bool(rejection),
        rc2_compatibility=True,
        rc3_compatibility=not (proposal.sandbox_created or proposal.execution_authorized),
        rejection_reasons=tuple(rejection),
        warnings=tuple(warnings),
    )


def compare_sandbox_proposals(proposals: tuple[SandboxProposal, ...]) -> SandboxComparison:
    isolation_score = {
        "documentation_only": 0.35,
        "logical_isolation": 0.5,
        "process_isolation": 0.65,
        "container_isolation": 0.82,
        "vm_isolation": 0.9,
        "air_gapped_evaluation": 0.96,
        "operator_only_handling": 0.3,
    }
    scoring = []
    for proposal in proposals:
        cost_penalty = {
            "documentation_only": 0.02,
            "logical_isolation": 0.05,
            "process_isolation": 0.12,
            "container_isolation": 0.2,
            "vm_isolation": 0.32,
            "air_gapped_evaluation": 0.45,
            "operator_only_handling": 0.01,
        }.get(proposal.required_isolation_level, 0.2)
        score = round(max(0.0, min(1.0, isolation_score.get(proposal.required_isolation_level, 0.5) + proposal.confidence / 4 - cost_penalty)), 4)
        scoring.append({
            "sandbox_proposal_id": proposal.sandbox_proposal_id,
            "isolation": proposal.required_isolation_level,
            "score": score,
            "reason": "ranked for operator review only",
        })
    ranked = tuple(item["sandbox_proposal_id"] for item in sorted(scoring, key=lambda item: item["score"], reverse=True))
    return SandboxComparison(
        comparison_id=_stable_id("sandbox-comparison", *ranked),
        ranked_sandbox_proposal_ids=ranked,
        scoring=tuple(scoring),
        recommendation="operator_review_ranked_sandbox_designs",
    )


def build_sandbox_review_summary(
    proposal: SandboxProposal,
    safety_review: SandboxSafetyReview,
    validation: SandboxValidation,
) -> SandboxReviewSummary:
    natural = (
        f"A sandbox design is considered because the originating proposal needs {proposal.required_isolation_level}. "
        f"The design is {validation.result} and remains proposal-only. "
        "No environment was created; the operator would still need to approve any future sandbox work."
    )
    return SandboxReviewSummary(
        summary_id=_stable_id("sandbox-review", proposal.sandbox_proposal_id, validation.result),
        sandbox_proposal_id=proposal.sandbox_proposal_id,
        why_needed=proposal.justification,
        proposed_isolation_model=proposal.required_isolation_level,
        assumptions=("Future execution, if any, would be separately approved.", "This pass only defines requirements."),
        limitations=("No sandbox runtime exists in this artifact.", "Resource estimates are planning estimates."),
        residual_risks=safety_review.findings,
        operator_decisions_required=proposal.operator_approval_requirements,
        natural_language=natural,
    )


def build_rc3_sandbox_episode(user_message: str, *, previous_episode: RC3Episode | None = None) -> RC3Episode:
    engineering_episode = previous_episode or build_rc3_engineering_episode(user_message)
    proposal_data = engineering_episode.developer_overlay["engineering_proposal"]
    engineering_proposal = EngineeringProposal(**proposal_data)
    engineering_validation = validate_engineering_proposal(engineering_proposal, user_message)
    requirement = analyze_sandbox_requirement(engineering_proposal)
    sandbox_proposal = build_sandbox_proposal(engineering_proposal, requirement)
    safety_review = review_sandbox_safety(sandbox_proposal)
    validation = validate_sandbox_proposal(sandbox_proposal)
    comparison = compare_sandbox_proposals((sandbox_proposal, _lower_isolation_alternative(engineering_proposal, requirement)))
    review = build_sandbox_review_summary(sandbox_proposal, safety_review, validation)
    overlay = dict(engineering_episode.developer_overlay)
    overlay.update({
        "entry_point": "build_rc3_sandbox_episode",
        "engineering_validation_for_sandbox": asdict(engineering_validation),
        "sandbox_requirement_analysis": asdict(requirement),
        "sandbox_proposal": asdict(sandbox_proposal),
        "isolation_analysis": {
            "classification": requirement.isolation_classification,
            "justification": requirement.justification,
            "no_environment_created": True,
        },
        "resource_estimates": asdict(sandbox_proposal.required_resources),
        "safety_findings": asdict(safety_review),
        "sandbox_validation": asdict(validation),
        "sandbox_comparison": asdict(comparison),
        "sandbox_review": asdict(review),
        "sandbox_created": False,
        "execution_authorized": False,
        "persistence_status": "ephemeral",
        "safety": dict(SAFETY_DEFAULTS),
    })
    return replace(
        engineering_episode,
        episode_id=_stable_id("sandbox-episode", engineering_episode.episode_id, sandbox_proposal.sandbox_proposal_id),
        developer_overlay=overlay,
        persistence_status="ephemeral",
        safety=dict(SAFETY_DEFAULTS),
    )


def build_rc3_d_sandbox_report(write_reports: bool = True) -> dict[str, Any]:
    episode = build_rc3_sandbox_episode(
        "Design the sandbox requirements for a future approved code-evaluation proposal. Do not create a sandbox, run code, mutate files, call providers, or touch DELTA-75."
    )
    overlay = episode.developer_overlay
    report = {
        "report": "RC3_D_SANDBOX_FOUNDATION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "episode": episode.to_dict(),
        "sandbox_validation_result": overlay["sandbox_validation"]["result"],
        "isolation_classification": overlay["sandbox_requirement_analysis"]["isolation_classification"],
        "safety_metadata_completeness": 1.0 if all(value is False for value in episode.safety.values()) else 0.0,
        "rc2_compatibility": 1.0,
        "recommendation": "READY_FOR_RC3_D_SANDBOX_BENCHMARK",
    }
    if write_reports:
        _write_report(report)
    return report


def _lower_isolation_alternative(
    engineering_proposal: EngineeringProposal,
    requirement: SandboxRequirement,
) -> SandboxProposal:
    alt_requirement = SandboxRequirement(
        requirement_id=_stable_id("sandbox-requirement-alt", requirement.requirement_id),
        recommendation="lower isolation alternative for operator comparison",
        required_capabilities=requirement.required_capabilities,
        isolation_classification="logical_isolation" if requirement.isolation_classification != "documentation_only" else "documentation_only",
        justification="Lower-cost alternative included for advisory comparison only.",
        confidence=max(0.45, requirement.confidence - 0.18),
        uncertainty="higher_than_primary",
    )
    return build_sandbox_proposal(engineering_proposal, alt_requirement)


def _write_report(report: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    overlay = report["episode"]["developer_overlay"]
    proposal = overlay["sandbox_proposal"]
    validation = overlay["sandbox_validation"]
    lines = [
        "# RC3-D Sandbox Foundation",
        "",
        f"Created: {report['created_at']}",
        f"Isolation: {report['isolation_classification']}",
        f"Sandbox proposal: {proposal['objective']}",
        f"Validation: {validation['result']}",
        f"Safety metadata completeness: {report['safety_metadata_completeness']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "No sandbox, container, VM, shell execution, filesystem mutation, plugin activation, provider call, commit, push, deployment, or DELTA-75 interaction occurred.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(build_rc3_d_sandbox_report(write_reports=True), indent=2, sort_keys=True))
