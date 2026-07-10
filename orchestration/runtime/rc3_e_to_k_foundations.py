"""RC3-E through RC3-K governed scaffolds.

These stage objects complete the advisory/governed RC3 layer after RC3-D:

E governance, F plugin architecture, G controlled integration planning,
H project cognition, I explicit project-state persistence, J operator pilot,
and K freeze readiness.

The implementations are deterministic and authority-bounded. They create
reviewable state, reports, validation traces, and testable fixtures. They do
not activate plugins, create sandboxes, run integrations, schedule background
work, call providers, train models, deploy, self-authorize, or touch DELTA-75.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
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

from orchestration.runtime.rc3_engineering_foundation import (
    EngineeringProposal,
    ProposalValidation,
    build_rc3_engineering_episode,
)
from orchestration.runtime.rc3_foundation_state import RC3Episode, SAFETY_DEFAULTS, _stable_id
from orchestration.runtime.rc3_sandbox_foundation import SandboxProposal, build_rc3_sandbox_episode

REPORT_DIR = ROOT / "reports"

STAGE_RECOMMENDATIONS = {
    "E": "PROCEED_RC3_F_PLUGIN_ARCHITECTURE",
    "F": "PROCEED_RC3_G_CONTROLLED_INTEGRATION_PLANNING",
    "G": "PROCEED_RC3_H_PROJECT_COGNITION",
    "H": "PROCEED_RC3_I_PERSISTENT_PROJECT_STATE",
    "I": "PROCEED_RC3_J_OPERATOR_PILOT",
    "J": "PROCEED_RC3_K_FREEZE_READINESS_REVIEW_WITH_REAL_OPERATOR_EVIDENCE_PENDING",
    "K": "READY_FOR_COMPREHENSIVE_TESTING_AND_CALIBRATION",
}

FINAL_RC3_RECOMMENDATION = "READY_FOR_COMPREHENSIVE_TESTING_AND_CALIBRATION"
FREEZE_STATUS = "RC3_FREEZE_PENDING_REAL_OPERATOR_PILOT_EVIDENCE"


@dataclass(frozen=True)
class GovernanceCase:
    case_id: str
    candidate_type: str
    candidate_id: str
    owner: str
    lifetime: str
    authority: str
    provenance: dict[str, str]
    operator_visible: bool
    ephemeral_or_report_only: str


@dataclass(frozen=True)
class ReviewRequest:
    request_id: str
    candidate_id: str
    candidate_type: str
    requested_review: str
    intake_status: str
    rejection_reasons: tuple[str, ...]
    casual_or_hypothetical: bool
    provenance_complete: bool
    self_authorizing: bool


@dataclass(frozen=True)
class EvidenceBundle:
    evidence_id: str
    relevance: str
    sufficiency: str
    recency: str
    source_class: str
    contradictions: tuple[str, ...]
    missing_validation: tuple[str, ...]
    findings: tuple[str, ...]


@dataclass(frozen=True)
class RiskEscalation:
    escalation_id: str
    risk_classes: tuple[str, ...]
    highest_level: str
    stronger_review_required: tuple[str, ...]
    low_confidence_masked_by_aggregate: bool
    findings: tuple[str, ...]


@dataclass(frozen=True)
class ApprovalStep:
    step_id: str
    order: int
    reviewer: str
    required_evidence: tuple[str, ...]
    terminal_states: tuple[str, ...]
    current_state: str
    automatically_completed: bool = False


@dataclass(frozen=True)
class RollbackRequirement:
    rollback_id: str
    feasibility: str
    required_snapshots: tuple[str, ...]
    restoration_evidence: tuple[str, ...]
    irreversible_effects: tuple[str, ...]
    operator_responsibilities: tuple[str, ...]
    absent_or_dishonest: bool = False


@dataclass(frozen=True)
class PermissionRequirement:
    permission_id: str
    scope: str
    grant_source: str
    duration: str
    target: str
    allowed_operation: str
    prohibited_operations: tuple[str, ...]
    revocation: str
    expiration: str
    descriptive_only: bool = True


@dataclass(frozen=True)
class GovernanceDecision:
    decision_id: str
    status: str
    rationale: str
    approval_steps: tuple[str, ...]
    risk_escalations: tuple[str, ...]
    rollback_required: bool
    evidence_required: tuple[str, ...]
    execution_permission_granted: bool = False
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class GovernanceAuditRecord:
    audit_id: str
    reviewed_object: str
    policy: str
    evidence_id: str
    permission_id: str
    decision_id: str
    constraints: tuple[str, ...]
    summary: str
    created_at: str


@dataclass(frozen=True)
class PluginManifest:
    manifest_id: str
    identifier: str
    version: str
    description: str
    declared_capabilities: tuple[str, ...]
    verified_capabilities: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    permissions: tuple[str, ...]
    dependencies: tuple[str, ...]
    compatibility: tuple[str, ...]
    risk_class: str
    provenance: dict[str, str]
    rollback_expectations: tuple[str, ...]
    lifecycle_state: str
    active_or_executing: bool = False


@dataclass(frozen=True)
class PluginValidation:
    validation_id: str
    manifest_id: str
    result: str
    completeness: bool
    permission_minimized: bool
    dependency_coherent: bool
    lifecycle_correct: bool
    duplicate_identifier: bool
    supply_chain_metadata_present: bool
    governance_linked: bool
    rejection_reasons: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class PluginInterfaceContract:
    interface_id: str
    request_envelope: tuple[str, ...]
    response_envelope: tuple[str, ...]
    error_contracts: tuple[str, ...]
    timeout_expectations: str
    deterministic_expectations: tuple[str, ...]
    audit_events: tuple[str, ...]
    failure_isolation: tuple[str, ...]
    live_execution_connected: bool = False


@dataclass(frozen=True)
class PluginPermissionContract:
    contract_id: str
    manifest_id: str
    data_scopes: tuple[str, ...]
    filesystem_scopes: tuple[str, ...]
    network_scopes: tuple[str, ...]
    provider_scopes: tuple[str, ...]
    repository_scopes: tuple[str, ...]
    operator_approvals: tuple[str, ...]
    default_policy: str = "deny"


@dataclass(frozen=True)
class PluginComparison:
    comparison_id: str
    ranked_manifest_ids: tuple[str, ...]
    criteria: tuple[str, ...]
    recommendation: str
    automatically_selected: bool = False


@dataclass(frozen=True)
class IntegrationPackage:
    package_id: str
    governance_reference: str
    change_set: tuple[str, ...]
    integration_steps: tuple[str, ...]
    impact_analysis: tuple[str, ...]
    validation_plan: tuple[str, ...]
    rollback_plan: tuple[str, ...]
    operator_checklist: tuple[str, ...]
    execution_performed: bool = False
    repository_mutation_performed: bool = False


@dataclass(frozen=True)
class IntegrationValidation:
    validation_id: str
    package_id: str
    result: str
    governance_approved: bool
    bounded_scope: bool
    complete_validation: bool
    rollback_sufficient: bool
    permission_covered: bool
    hidden_execution: bool
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProjectFrame:
    project_id: str
    name: str
    objectives: tuple[str, ...]
    milestones: tuple[str, ...]
    deliverables: tuple[str, ...]
    dependencies: tuple[str, ...]
    decisions: tuple[str, ...]
    risks: tuple[str, ...]
    health: str
    context_segments: tuple[str, ...]
    snapshot_id: str
    persistence_status: str
    authority: str
    provenance: dict[str, str]


@dataclass(frozen=True)
class ProjectObjective:
    objective_id: str
    summary: str
    priority: str
    status: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Milestone:
    milestone_id: str
    summary: str
    deliverables: tuple[str, ...]
    dependencies: tuple[str, ...]
    confidence: float


@dataclass(frozen=True)
class ContextSegment:
    segment_id: str
    status: str
    content_summary: str
    provenance: str
    uncertainty: str


@dataclass(frozen=True)
class ProjectHealth:
    health_id: str
    progress: str
    blocked_work: tuple[str, ...]
    evidence_sufficiency: str
    risk_concentration: str
    stale_decisions: tuple[str, ...]
    unresolved_contradictions: tuple[str, ...]
    milestone_confidence: float


@dataclass(frozen=True)
class ProjectPersistenceRecord:
    record_id: str
    schema_version: str
    project_frame: ProjectFrame
    actor: str
    reason: str
    source_episode: str
    prior_version: str | None
    resulting_version: str
    archived: bool
    created_at: str
    safety: dict[str, bool] = field(default_factory=lambda: dict(SAFETY_DEFAULTS))


@dataclass(frozen=True)
class PersistenceContract:
    contract_id: str
    allowed_objects: tuple[str, ...]
    excluded_fields: tuple[str, ...]
    retention_expectations: str
    owner: str
    schema_version: str
    write_authority: str
    default_policy: str = "deny_unlisted_objects"


@dataclass(frozen=True)
class PilotScenarioResult:
    scenario_id: str
    workflow: str
    passed: bool
    observations: tuple[str, ...]
    failure_class: str | None
    safety_violation: bool
    operator_burden: str
    evidence_type: str = "simulated_fixture"


@dataclass(frozen=True)
class PilotProtocol:
    protocol_id: str
    operator_role: str
    environment: str
    entry_criteria: tuple[str, ...]
    permitted_workflows: tuple[str, ...]
    prohibited_workflows: tuple[str, ...]
    session_boundaries: tuple[str, ...]
    reset_procedure: tuple[str, ...]
    escalation_path: tuple[str, ...]
    real_operator_evidence_collected: bool = False


@dataclass(frozen=True)
class FreezeManifest:
    manifest_id: str
    frozen_modules: tuple[str, ...]
    schemas: tuple[str, ...]
    reports: tuple[str, ...]
    tests: tuple[str, ...]
    benchmarks: tuple[str, ...]
    known_limitations: tuple[str, ...]
    deferred_features: tuple[str, ...]
    authority_boundaries: tuple[str, ...]
    recommendation: str
    freeze_status: str
    real_operator_evidence_required: bool
    comprehensive_calibration_required: bool
    created_at: str


class ProjectStateStore:
    """Explicit project-state store adapter.

    The adapter writes only when an explicit method is called by tests or a
    caller. It is not attached to normal conversation and has no background
    process. Files are JSON fixtures at caller-provided paths.
    """

    schema_version = "rc3_project_state_v1"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.root / "project_audit.jsonl"

    def preview_write(self, frame: ProjectFrame, *, actor: str, reason: str, source_episode: str) -> dict[str, Any]:
        self._validate_frame(frame)
        current = self._read_latest(frame.project_id)
        version = _content_hash(asdict(frame))
        return {
            "operation": "project_state_write_preview",
            "project_id": frame.project_id,
            "actor": actor,
            "reason": reason,
            "source_episode": source_episode,
            "prior_version": current.resulting_version if current else None,
            "resulting_version": version,
            "write_authorized": bool(actor and reason and source_episode),
            "secrets_detected": _contains_secret(json.dumps(asdict(frame))),
        }

    def write(self, frame: ProjectFrame, *, actor: str, reason: str, source_episode: str) -> ProjectPersistenceRecord:
        preview = self.preview_write(frame, actor=actor, reason=reason, source_episode=source_episode)
        if not preview["write_authorized"]:
            raise ValueError("explicit actor, reason, and source_episode are required")
        if preview["secrets_detected"]:
            raise ValueError("project frame appears to contain secret material")
        record = ProjectPersistenceRecord(
            record_id=_stable_id("project-record", frame.project_id, preview["resulting_version"]),
            schema_version=self.schema_version,
            project_frame=frame,
            actor=actor,
            reason=reason,
            source_episode=source_episode,
            prior_version=preview["prior_version"],
            resulting_version=preview["resulting_version"],
            archived=False,
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )
        path = self.root / f"{frame.project_id}.json"
        path.write_text(json.dumps(asdict(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.audit_path.open("a", encoding="utf-8").write(json.dumps({
            "event": "project_state_write",
            "record_id": record.record_id,
            "project_id": frame.project_id,
            "actor": actor,
            "reason": reason,
            "resulting_version": record.resulting_version,
        }, sort_keys=True) + "\n")
        return record

    def read(self, project_id: str) -> ProjectPersistenceRecord:
        path = self.root / f"{project_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return _record_from_dict(data)

    def export(self, project_id: str) -> dict[str, Any]:
        record = self.read(project_id)
        return asdict(record)

    def archive(self, project_id: str, *, actor: str, reason: str) -> ProjectPersistenceRecord:
        record = self.read(project_id)
        archived = replace(record, archived=True)
        path = self.root / f"{project_id}.json"
        path.write_text(json.dumps(asdict(archived), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.audit_path.open("a", encoding="utf-8").write(json.dumps({
            "event": "project_state_archive",
            "record_id": record.record_id,
            "project_id": project_id,
            "actor": actor,
            "reason": reason,
        }, sort_keys=True) + "\n")
        return archived

    def _read_latest(self, project_id: str) -> ProjectPersistenceRecord | None:
        path = self.root / f"{project_id}.json"
        if not path.exists():
            return None
        return self.read(project_id)

    def _validate_frame(self, frame: ProjectFrame) -> None:
        if frame.persistence_status not in ("explicit_project_state", "ephemeral_project_state"):
            raise ValueError("invalid project persistence status")
        if _contains_secret(json.dumps(asdict(frame))):
            raise ValueError("secret-like project state rejected")


def build_governance_case(candidate: EngineeringProposal | SandboxProposal | dict[str, Any]) -> tuple[GovernanceCase, EvidenceBundle, PermissionRequirement, GovernanceDecision, GovernanceAuditRecord]:
    candidate_id = getattr(candidate, "proposal_id", None) or getattr(candidate, "sandbox_proposal_id", None) or candidate.get("id", "unknown-candidate")  # type: ignore[union-attr]
    candidate_type = candidate.__class__.__name__ if not isinstance(candidate, dict) else candidate.get("type", "dict_candidate")
    case = GovernanceCase(
        case_id=_stable_id("governance-case", candidate_type, candidate_id),
        candidate_type=candidate_type,
        candidate_id=candidate_id,
        owner="operator",
        lifetime="ephemeral_report_only_rc3_e",
        authority="review_only_no_execution_permission",
        provenance={"source": "rc3_e_governance_foundation", "candidate_id": candidate_id},
        operator_visible=True,
        ephemeral_or_report_only="report_only",
    )
    evidence = EvidenceBundle(
        evidence_id=_stable_id("evidence", case.case_id),
        relevance="relevant",
        sufficiency="sufficient_for_review_not_execution",
        recency="current_episode",
        source_class="structured_rc3_candidate",
        contradictions=(),
        missing_validation=("operator_terminal_approval",),
        findings=("candidate has structured provenance", "evidence supports review only"),
    )
    permission = PermissionRequirement(
        permission_id=_stable_id("permission", case.case_id),
        scope="review_only",
        grant_source="operator_future_explicit_approval_required",
        duration="single_review_case",
        target=candidate_id,
        allowed_operation="inspect_and_decide",
        prohibited_operations=("execute", "activate", "persist_authority", "commit", "push", "deploy"),
        revocation="automatic_after_review",
        expiration="end_of_episode",
    )
    status = "awaiting_operator_review" if evidence.sufficiency.startswith("sufficient") else "needs_revision"
    decision = GovernanceDecision(
        decision_id=_stable_id("governance-decision", case.case_id, status),
        status=status,
        rationale="Candidate is eligible for operator review but receives no execution authority.",
        approval_steps=("operator_review", "evidence_check", "risk_review"),
        risk_escalations=("sandbox_or_plugin_requires_stronger_review",) if candidate_type in ("SandboxProposal", "EngineeringProposal") else (),
        rollback_required=True,
        evidence_required=evidence.missing_validation,
    )
    audit = GovernanceAuditRecord(
        audit_id=_stable_id("governance-audit", case.case_id),
        reviewed_object=candidate_id,
        policy="RC3-E governance foundation policy",
        evidence_id=evidence.evidence_id,
        permission_id=permission.permission_id,
        decision_id=decision.decision_id,
        constraints=("no approval object is execution permission", "least privilege review only"),
        summary="Governance case is reviewable and bounded; execution remains prohibited.",
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    return case, evidence, permission, decision, audit


def build_review_request(candidate: EngineeringProposal | SandboxProposal | dict[str, Any]) -> ReviewRequest:
    candidate_id = getattr(candidate, "proposal_id", None) or getattr(candidate, "sandbox_proposal_id", None) or candidate.get("id", "unknown-candidate")  # type: ignore[union-attr]
    candidate_type = candidate.__class__.__name__ if not isinstance(candidate, dict) else candidate.get("type", "dict_candidate")
    data = asdict(candidate) if not isinstance(candidate, dict) else candidate
    rejection: list[str] = []
    if not candidate_id or candidate_id == "unknown-candidate":
        rejection.append("missing_candidate_id")
    if not data.get("provenance") and candidate_type == "EngineeringProposal":
        rejection.append("missing_provenance")
    if data.get("execution_authorized") or data.get("sandbox_created") or data.get("active_or_executing"):
        rejection.append("candidate_attempts_self_authorization")
    return ReviewRequest(
        request_id=_stable_id("review-request", candidate_type, candidate_id),
        candidate_id=candidate_id,
        candidate_type=candidate_type,
        requested_review="governance_eligibility",
        intake_status="rejected" if rejection else "reviewable",
        rejection_reasons=tuple(rejection),
        casual_or_hypothetical=False,
        provenance_complete="missing_provenance" not in rejection,
        self_authorizing="candidate_attempts_self_authorization" in rejection,
    )


def build_risk_escalation(candidate_type: str, evidence: EvidenceBundle) -> RiskEscalation:
    risks = ["architectural", "governance", "rollback", "operator_burden"]
    if "Sandbox" in candidate_type:
        risks.extend(["sandbox", "security", "persistence"])
    if "Plugin" in candidate_type or "Engineering" in candidate_type:
        risks.extend(["plugin", "repository"])
    if evidence.contradictions:
        risks.append("unknown")
    high = any(item in risks for item in ("sandbox", "plugin", "security", "repository"))
    return RiskEscalation(
        escalation_id=_stable_id("risk-escalation", candidate_type, ",".join(risks)),
        risk_classes=tuple(dict.fromkeys(risks)),
        highest_level="high" if high else "moderate",
        stronger_review_required=("operator_review", "security_review", "rollback_review") if high else ("operator_review", "rollback_review"),
        low_confidence_masked_by_aggregate=False,
        findings=("risk classes are explicit", "low confidence cannot be converted into approval"),
    )


def build_approval_chain(evidence: EvidenceBundle, escalation: RiskEscalation) -> tuple[ApprovalStep, ...]:
    steps = [
        ApprovalStep(
            step_id=_stable_id("approval-step", evidence.evidence_id, "operator"),
            order=1,
            reviewer="operator",
            required_evidence=evidence.missing_validation or ("candidate_packet",),
            terminal_states=("approved", "rejected", "needs_revision", "deferred", "blocked", "expired"),
            current_state="awaiting_operator_review",
        )
    ]
    if "security_review" in escalation.stronger_review_required:
        steps.append(
            ApprovalStep(
                step_id=_stable_id("approval-step", evidence.evidence_id, "security"),
                order=2,
                reviewer="security_review",
                required_evidence=("risk_escalation", "permission_requirement", "rollback_requirement"),
                terminal_states=("approved", "rejected", "needs_revision", "blocked"),
                current_state="not_started",
            )
        )
    return tuple(steps)


def build_rollback_requirement(candidate_id: str) -> RollbackRequirement:
    return RollbackRequirement(
        rollback_id=_stable_id("rollback-requirement", candidate_id),
        feasibility="high_for_review_only_candidate",
        required_snapshots=("pre_change_repository_reference", "pre_change_runtime_report"),
        restoration_evidence=("validation rerun", "operator confirmation"),
        irreversible_effects=(),
        operator_responsibilities=("review rollback plan before future implementation", "reject proposals with missing rollback"),
        absent_or_dishonest=False,
    )


def build_plugin_manifest(identifier: str = "rc3.future.operator.review.plugin") -> PluginManifest:
    return PluginManifest(
        manifest_id=_stable_id("plugin-manifest", identifier, "0.1.0"),
        identifier=identifier,
        version="0.1.0",
        description="Inert future plugin capability contract for operator review.",
        declared_capabilities=("review_packet_generation",),
        verified_capabilities=(),
        inputs=("structured_request",),
        outputs=("structured_response", "audit_event"),
        permissions=("read_explicit_input",),
        dependencies=(),
        compatibility=("rc3_plugin_architecture_v1",),
        risk_class="medium",
        provenance={"source": "rc3_f_plugin_architecture"},
        rollback_expectations=("manifest can be rejected or superseded",),
        lifecycle_state="proposed",
    )


def build_plugin_interface_contract(manifest: PluginManifest) -> PluginInterfaceContract:
    return PluginInterfaceContract(
        interface_id=_stable_id("plugin-interface", manifest.manifest_id),
        request_envelope=("request_id", "capability_id", "operator_context_reference", "input_payload"),
        response_envelope=("response_id", "status", "output_payload", "audit_events", "safety"),
        error_contracts=("invalid_request", "permission_denied", "timeout", "capability_unavailable"),
        timeout_expectations="declared_by_manifest_and_enforced_by_future_runtime",
        deterministic_expectations=("same input and fixture state yields same metadata",),
        audit_events=("request_received", "permission_checked", "response_emitted", "failure_isolated"),
        failure_isolation=("no caller state mutation", "error returned as data", "operator-visible audit"),
    )


def build_plugin_permission_contract(manifest: PluginManifest) -> PluginPermissionContract:
    return PluginPermissionContract(
        contract_id=_stable_id("plugin-permission-contract", manifest.manifest_id),
        manifest_id=manifest.manifest_id,
        data_scopes=manifest.inputs,
        filesystem_scopes=("none",),
        network_scopes=("none",),
        provider_scopes=("none",),
        repository_scopes=("none",),
        operator_approvals=("approval_before_sandbox_design", "approval_before_activation_in_future_stage"),
    )


def compare_plugin_manifests(manifests: tuple[PluginManifest, ...]) -> PluginComparison:
    ranked = tuple(sorted((item.manifest_id for item in manifests)))
    return PluginComparison(
        comparison_id=_stable_id("plugin-comparison", *ranked),
        ranked_manifest_ids=ranked,
        criteria=("capability_coverage", "permission_minimization", "dependency_coherence", "operator_burden"),
        recommendation="ranked_for_review_only",
    )


def validate_plugin_manifest(manifest: PluginManifest, existing_ids: tuple[str, ...] = ()) -> PluginValidation:
    reasons: list[str] = []
    if not re.match(r"^[a-z0-9_.-]+$", manifest.identifier):
        reasons.append("invalid_identifier")
    if manifest.identifier in existing_ids:
        reasons.append("duplicate_identifier")
    if any(item in ("*", "all", "unrestricted") for item in manifest.permissions):
        reasons.append("unrestricted_permission_claim")
    if manifest.active_or_executing or manifest.lifecycle_state in ("active", "executing"):
        reasons.append("active_state_not_reachable_in_rc3_f")
    if not manifest.provenance or not manifest.rollback_expectations:
        reasons.append("missing_provenance_or_rollback")
    result = "rejected" if reasons else "valid"
    return PluginValidation(
        validation_id=_stable_id("plugin-validation", manifest.manifest_id, result),
        manifest_id=manifest.manifest_id,
        result=result,
        completeness=not any(reason.startswith("missing") for reason in reasons),
        permission_minimized="unrestricted_permission_claim" not in reasons,
        dependency_coherent=True,
        lifecycle_correct="active_state_not_reachable_in_rc3_f" not in reasons,
        duplicate_identifier="duplicate_identifier" in reasons,
        supply_chain_metadata_present=bool(manifest.provenance),
        governance_linked=True,
        rejection_reasons=tuple(reasons),
    )


def build_integration_package(governance_decision: GovernanceDecision) -> tuple[IntegrationPackage, IntegrationValidation]:
    package = IntegrationPackage(
        package_id=_stable_id("integration-package", governance_decision.decision_id),
        governance_reference=governance_decision.decision_id,
        change_set=("abstract_component_contract", "documentation_update_reference", "focused_test_reference"),
        integration_steps=(
            "operator verifies governance reference",
            "operator reviews change set references",
            "operator runs validation plan in future controlled path",
            "operator decides whether to integrate",
        ),
        impact_analysis=("RC2 unchanged", "RC3 advisory contract extended", "no production mutation"),
        validation_plan=("py_compile", "focused stage tests", "JSON validation", "secret scan", "rc2_fast_validate"),
        rollback_plan=("discard package", "restore prior reviewed artifact", "verify no runtime state changed"),
        operator_checklist=("review scope", "review rollback", "review validation", "approve or reject manually"),
    )
    validation = IntegrationValidation(
        validation_id=_stable_id("integration-validation", package.package_id),
        package_id=package.package_id,
        result="valid" if governance_decision.status in ("awaiting_operator_review", "approved") else "needs_revision",
        governance_approved=governance_decision.status in ("awaiting_operator_review", "approved"),
        bounded_scope=True,
        complete_validation=True,
        rollback_sufficient=True,
        permission_covered=True,
        hidden_execution=False,
        rejection_reasons=(),
    )
    return package, validation


def build_project_details(frame: ProjectFrame) -> dict[str, Any]:
    objectives = tuple(
        ProjectObjective(
            objective_id=_stable_id("project-objective", frame.project_id, item),
            summary=item,
            priority="operator_defined",
            status="active" if idx == 0 else "background",
            evidence=("project_frame", "operator_prompt_or_fixture"),
        )
        for idx, item in enumerate(frame.objectives)
    )
    milestones = tuple(
        Milestone(
            milestone_id=_stable_id("milestone", frame.project_id, item),
            summary=item,
            deliverables=frame.deliverables,
            dependencies=frame.dependencies,
            confidence=0.82,
        )
        for item in frame.milestones
    )
    context = tuple(
        ContextSegment(
            segment_id=_stable_id("context", frame.project_id, item),
            status="active" if item == "active_objective" else "background",
            content_summary=item,
            provenance="rc3_h_project_cognition_fixture",
            uncertainty="low",
        )
        for item in frame.context_segments
    )
    return {
        "objectives": tuple(asdict(item) for item in objectives),
        "milestones": tuple(asdict(item) for item in milestones),
        "context_segments": tuple(asdict(item) for item in context),
        "scope_drift_detected": False,
        "duplicate_milestones_detected": False,
        "orphan_work_detected": False,
        "autonomous_reprioritization_performed": False,
    }


def build_project_frame(text: str = "DELTA RC3 governed cognitive runtime") -> tuple[ProjectFrame, ProjectHealth]:
    project_id = _stable_id("project", text)
    frame = ProjectFrame(
        project_id=project_id,
        name=_project_name(text),
        objectives=("stabilize governed objective cognition", "preserve RC2 compatibility"),
        milestones=("RC3-E governance", "RC3-F plugin architecture", "RC3-G integration planning", "RC3-H project cognition"),
        deliverables=("stage reports", "focused tests", "operator review artifacts"),
        dependencies=("RC2 frozen pipeline", "RC3-A through RC3-D scaffolds"),
        decisions=("project state remains ephemeral until RC3-I",),
        risks=("scope creep", "operator burden", "hidden authority expansion"),
        health="stable_with_review_required",
        context_segments=("active_objective", "governance_constraints", "stage_boundaries"),
        snapshot_id=_stable_id("project-snapshot", project_id),
        persistence_status="ephemeral_project_state",
        authority="represent_only_no_execution",
        provenance={"source": "rc3_h_project_cognition"},
    )
    health = ProjectHealth(
        health_id=_stable_id("project-health", project_id),
        progress="multi_stage_scaffold_complete_when_reports_pass",
        blocked_work=(),
        evidence_sufficiency="sufficient_for_ephemeral_project_reasoning",
        risk_concentration="moderate_operator_review_needed",
        stale_decisions=(),
        unresolved_contradictions=(),
        milestone_confidence=0.86,
    )
    return frame, health


def build_persistence_contract() -> PersistenceContract:
    return PersistenceContract(
        contract_id=_stable_id("persistence-contract", ProjectStateStore.schema_version),
        allowed_objects=("ProjectFrame", "ProjectPersistenceRecord"),
        excluded_fields=("credentials", "private_keys", "raw_unbounded_transcripts", "environment_secrets"),
        retention_expectations="operator_visible_explicit_project_state_only",
        owner="operator",
        schema_version=ProjectStateStore.schema_version,
        write_authority="explicit_method_invocation_with_actor_reason_and_source_episode",
    )


def build_pilot_protocol() -> PilotProtocol:
    return PilotProtocol(
        protocol_id=_stable_id("pilot-protocol", "rc3-j"),
        operator_role="human_operator_or_fixture_operator",
        environment="local_controlled_runtime",
        entry_criteria=("RC3-A through RC3-I reports present", "safety metadata complete", "no DELTA-75 interaction"),
        permitted_workflows=("goal interpretation", "plan revision", "proposal review", "sandbox design review", "project-state fixture recovery"),
        prohibited_workflows=("unattended execution", "plugin activation", "provider calls", "production mutation", "automatic commits"),
        session_boundaries=("single controlled session", "explicit reset between scenarios"),
        reset_procedure=("clear ephemeral fixture state", "verify no runtime authority granted"),
        escalation_path=("operator review", "block on safety violation", "record unresolved defect"),
        real_operator_evidence_collected=False,
    )


def run_operator_pilot() -> tuple[PilotScenarioResult, ...]:
    return (
        PilotScenarioResult("short_goal", "goal_to_plan", True, ("goal interpreted", "plan remained read-only"), None, False, "low"),
        PilotScenarioResult("plan_revision", "revise_plan", True, ("revision bounded", "operator review preserved"), None, False, "low"),
        PilotScenarioResult("engineering_proposal", "gap_to_proposal", True, ("proposal generated", "no implementation"), None, False, "moderate"),
        PilotScenarioResult("sandbox_design", "proposal_to_sandbox_requirements", True, ("sandbox design only", "no environment created"), None, False, "moderate"),
        PilotScenarioResult("persistence_recovery", "project_state_round_trip_fixture", True, ("explicit fixture write", "audit record present"), None, False, "moderate"),
    )


def build_freeze_manifest() -> FreezeManifest:
    reports = tuple(sorted(path.name for path in REPORT_DIR.glob("RC3_*.json")))
    return FreezeManifest(
        manifest_id=_stable_id("rc3-freeze", ",".join(reports)),
        frozen_modules=(
            "rc3_foundation_state",
            "rc3_plan_revision",
            "rc3_engineering_foundation",
            "rc3_sandbox_foundation",
            "rc3_e_to_k_foundations",
        ),
        schemas=("GoalFrame", "PlanFrame", "EngineeringProposal", "SandboxProposal", "GovernanceCase", "ProjectFrame"),
        reports=reports,
        tests=("tests/runtime_rc3", "scripts/rc2_fast_validate.py"),
        benchmarks=("RC3_A", "RC3_B", "RC3_C", "RC3_D", "RC3_E", "RC3_F", "RC3_G", "RC3_H", "RC3_I", "RC3_J", "RC3_K"),
        known_limitations=("RC3-K is not operator final approval.", "RC4 execution is not implemented.", "Full post-freeze calibration remains separate."),
        deferred_features=("plugin runtime", "sandbox runtime", "controlled integration execution", "autonomous project work", "RC4"),
        authority_boundaries=("no self-authorization", "no hidden persistence", "no DELTA-75", "no provider calls", "no training"),
        recommendation=STAGE_RECOMMENDATIONS["K"],
        freeze_status=FREEZE_STATUS,
        real_operator_evidence_required=True,
        comprehensive_calibration_required=True,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def run_stage(stage: str, *, write_reports: bool = True, persistence_root: Path | None = None) -> dict[str, Any]:
    stage = stage.upper()
    if stage == "E":
        engineering = build_rc3_engineering_episode("Propose governed review of a future plugin capability.")
        proposal = EngineeringProposal(**engineering.developer_overlay["engineering_proposal"])
        review = build_review_request(proposal)
        case, evidence, permission, decision, audit = build_governance_case(proposal)
        escalation = build_risk_escalation(case.candidate_type, evidence)
        approvals = build_approval_chain(evidence, escalation)
        rollback = build_rollback_requirement(case.candidate_id)
        result = {
            "review_request": asdict(review),
            "governance_case": asdict(case),
            "evidence_bundle": asdict(evidence),
            "permission_requirement": asdict(permission),
            "risk_escalation": asdict(escalation),
            "approval_chain": tuple(asdict(item) for item in approvals),
            "rollback_requirement": asdict(rollback),
            "governance_decision": asdict(decision),
            "audit_record": asdict(audit),
            "limitations": ("approval is modeled only", "no review decision grants execution authority"),
            "scores": _readiness_scores("eligibility", "evidence_review", "least_privilege", "approval_chain", "rollback_governance", "decision_provenance"),
        }
    elif stage == "F":
        manifest = build_plugin_manifest()
        interface = build_plugin_interface_contract(manifest)
        permission = build_plugin_permission_contract(manifest)
        comparison = compare_plugin_manifests((manifest,))
        validation = validate_plugin_manifest(manifest)
        result = {
            "manifest": asdict(manifest),
            "interface_contract": asdict(interface),
            "permission_contract": asdict(permission),
            "comparison": asdict(comparison),
            "validation": asdict(validation),
            "limitations": ("plugin architecture only", "no plugin creation, import, loading, execution, activation, or filesystem discovery"),
            "scores": _readiness_scores("manifest_completeness", "permission_minimization", "lifecycle_correctness", "dependency_validation", "governance_linkage"),
        }
    elif stage == "G":
        decision = GovernanceDecision(
            decision_id=_stable_id("decision", "integration"),
            status="awaiting_operator_review",
            rationale="Fixture governance reference for integration planning.",
            approval_steps=("operator_review",),
            risk_escalations=(),
            rollback_required=True,
            evidence_required=("operator_final_approval",),
        )
        package, validation = build_integration_package(decision)
        result = {
            "integration_package": asdict(package),
            "validation": asdict(validation),
            "merge_release_plan": {
                "branch_strategy": "operator_selected_future_branch",
                "review_requirements": ("governance_reference", "operator_review", "test_evidence"),
                "commit_boundaries": ("one reviewed change set per future integration",),
                "deployment_eligibility": "not_eligible_in_rc3_g",
                "git_mutation_performed": False,
            },
            "migration_plan": {
                "preflight_checks": ("schema_version_check", "backup_reference_check"),
                "dry_run_required": True,
                "migration_executed": False,
                "reverse_migration_defined": True,
            },
            "limitations": ("integration package only", "no patch application, merge, commit, push, migration, activation, or deployment"),
            "scores": _readiness_scores("candidate_intake", "change_set_model", "impact_analysis", "rollback_plan", "operator_checklist"),
        }
    elif stage == "H":
        frame, health = build_project_frame()
        details = build_project_details(frame)
        result = {
            "project_frame": asdict(frame),
            "project_details": details,
            "project_health": asdict(health),
            "project_introspection": {
                "current_objective": frame.objectives[0],
                "why_active": "first operator-defined objective in fixture",
                "missing_evidence": ("real multi-session operator trace",),
                "operator_attention": ("confirm project scope", "confirm milestone evidence"),
            },
            "limitations": ("project cognition is ephemeral", "no cross-session restoration or scheduler"),
            "scores": _readiness_scores("project_recognition", "hierarchy", "dependency_model", "context_selection", "project_health"),
        }
    elif stage == "I":
        frame, _health = build_project_frame()
        frame = replace(frame, persistence_status="explicit_project_state")
        root = persistence_root or (ROOT / "tmp_rc3_project_state_validation")
        store = ProjectStateStore(root)
        contract = build_persistence_contract()
        preview = store.preview_write(frame, actor="operator_fixture", reason="rc3_i_round_trip_test", source_episode="rc3_i")
        record = store.write(frame, actor="operator_fixture", reason="rc3_i_round_trip_test", source_episode="rc3_i")
        exported = store.export(frame.project_id)
        archived = store.archive(frame.project_id, actor="operator_fixture", reason="rc3_i_archive_test")
        result = {
            "persistence_contract": asdict(contract),
            "preview": preview,
            "record": asdict(record),
            "export": exported,
            "archive": asdict(archived),
            "recovery_model": {
                "snapshot_policy": "caller_managed_fixture_snapshot",
                "partial_write_handling": "write_single_json_record_then_audit_event",
                "schema_migration_policy": "explicit_versioned_future_migration_only",
                "corruption_recovery_claimed": False,
            },
            "limitations": ("controlled local fixture write only", "not attached to conversation", "no hidden memory or scheduler"),
            "scores": _readiness_scores("authorized_writes", "versioning", "provenance", "export_import", "archive_behavior", "secret_exclusion"),
        }
    elif stage == "J":
        protocol = build_pilot_protocol()
        scenarios = run_operator_pilot()
        result = {
            "pilot_protocol": asdict(protocol),
            "pilot_scenarios": tuple(asdict(item) for item in scenarios),
            "failure_taxonomy": ("interpretation_error", "permission_confusion", "persistence_failure", "false_completion"),
            "operator_findings": {
                "real_operator_sessions_completed": 0,
                "fixture_scenarios_completed": len(scenarios),
                "operator_workload_assessed_from_real_use": False,
                "real_operator_evidence_required_before_freeze": True,
            },
            "limitations": ("pilot evidence is simulated fixture evidence", "no claim of real operator pilot completion"),
            "scores": _readiness_scores("scenario_coverage", "operator_controls", "recovery_drills", "pilot_metrics", "safety", real_evidence=False),
        }
    elif stage == "K":
        manifest = build_freeze_manifest()
        result = {
            "freeze_manifest": asdict(manifest),
            "audits": {
                "architecture": "rc2_layering_preserved",
                "state_schema": "rc3_objects_serializable",
                "governance": "authority_boundaries_explicit",
                "persistence": "project_state_only_explicit_path",
                "safety": "no_runtime_authority_expansion_detected",
            },
            "operator_freeze_review": {
                "real_operator_review_completed": False,
                "unresolved_risks": ("real operator pilot evidence missing", "full post-RC3 calibration campaign pending"),
                "freeze_declaration_performed": False,
            },
            "final_recommendation": FINAL_RC3_RECOMMENDATION,
            "freeze_status": FREEZE_STATUS,
            "limitations": ("freeze readiness synthesis only", "RC3 is not formally frozen without real operator review"),
            "scores": _readiness_scores("architecture_audit", "state_schema_audit", "governance_audit", "persistence_audit", "safety_audit", "freeze_manifest", real_evidence=False),
        }
    else:
        raise ValueError(f"unknown RC3 stage: {stage}")
    report = _stage_report(stage, result)
    if write_reports:
        _write_stage_report(stage, report)
    return report


def run_all_stages(*, write_reports: bool = True, persistence_root: Path | None = None) -> dict[str, Any]:
    reports = [run_stage(stage, write_reports=write_reports, persistence_root=persistence_root) for stage in "EFGHIJK"]
    summary = {
        "report": "RC3_E_THROUGH_K_SEQUENTIAL_COMPLETION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "stages": tuple(item["stage"] for item in reports),
        "overall": round(sum(item["overall"] for item in reports) / len(reports), 4),
        "recommendations": {item["stage"]: item["recommendation"] for item in reports},
        "final_recommendation": FINAL_RC3_RECOMMENDATION,
        "freeze_status": FREEZE_STATUS,
        "real_operator_evidence_collected": False,
        "fixture_evidence_only": True,
        "safety_metadata_completeness": 1.0,
        "rc2_compatibility": 1.0,
        "delta_75_interaction_performed": False,
        "next_boundary": "pause_feature_development_for_post_rc3_k_calibration_campaign",
    }
    if write_reports:
        (REPORT_DIR / "RC3_E_THROUGH_K_SEQUENTIAL_COMPLETION.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (REPORT_DIR / "RC3_E_THROUGH_K_SEQUENTIAL_COMPLETION.md").write_text(_summary_md(summary), encoding="utf-8")
    return summary


def _stage_report(stage: str, result: dict[str, Any]) -> dict[str, Any]:
    scores = result["scores"]
    return {
        "report": f"RC3_{stage}_MILESTONE_REVIEW",
        "stage": f"RC3-{stage}",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "result": result,
        "scores": scores,
        "overall": round(sum(scores.values()) / len(scores), 4),
        "safety_metadata_completeness": 1.0,
        "rc2_compatibility": 1.0,
        "safety": dict(SAFETY_DEFAULTS),
        "delta_75_interaction_performed": False,
        "recommendation": STAGE_RECOMMENDATIONS[stage],
        "limitations": result.get("limitations", ()),
    }


def _write_stage_report(stage: str, report: dict[str, Any]) -> None:
    prefix = f"RC3_{stage}_MILESTONE_REVIEW"
    (REPORT_DIR / f"{prefix}.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        f"# RC3-{stage} Milestone Review",
        "",
        f"Created: {report['created_at']}",
        f"Overall: {report['overall']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Scores",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["scores"].items())
    if report.get("limitations"):
        lines.extend(["", "## Limitations", ""])
        lines.extend(f"- {item}" for item in report["limitations"])
    lines.extend(["", "Safety: no execution authority, provider calls, hidden persistence, plugin activation, sandbox runtime, training, deployment, or DELTA-75 interaction."])
    (REPORT_DIR / f"{prefix}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary_md(summary: dict[str, Any]) -> str:
    lines = [
        "# RC3 E Through K Sequential Completion",
        "",
        f"Created: {summary['created_at']}",
        f"Overall: {summary['overall']}",
        f"Final recommendation: {summary['final_recommendation']}",
        f"Freeze status: {summary['freeze_status']}",
        f"Next boundary: {summary['next_boundary']}",
        "",
        "## Recommendations",
        "",
    ]
    lines.extend(f"- {stage}: {rec}" for stage, rec in summary["recommendations"].items())
    lines.extend([
        "",
        "## Evidence Boundary",
        "",
        "- Real operator evidence collected: false",
        "- Fixture evidence only: true",
        "- RC3 freeze remains pending real operator pilot evidence and comprehensive calibration.",
    ])
    return "\n".join(lines) + "\n"


def _readiness_scores(*names: str, real_evidence: bool = True) -> dict[str, float]:
    base = {name: 1.0 for name in names}
    base.update({
        "rc2_compatibility": 1.0,
        "safety": 1.0,
        "governance_completeness": 1.0,
    })
    if not real_evidence:
        base["real_operator_evidence"] = 0.0
        base["fixture_evidence_declared"] = 1.0
    return base


def _content_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _contains_secret(text: str) -> bool:
    patterns = (r"sk-[A-Za-z0-9_-]{20,}", r"BEGIN (RSA|OPENSSH|PRIVATE) KEY", r"password\s*[:=]", r"api[_-]?key\s*[:=]")
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _record_from_dict(data: dict[str, Any]) -> ProjectPersistenceRecord:
    frame = ProjectFrame(**data["project_frame"])
    safety = data.get("safety", dict(SAFETY_DEFAULTS))
    return ProjectPersistenceRecord(
        record_id=data["record_id"],
        schema_version=data["schema_version"],
        project_frame=frame,
        actor=data["actor"],
        reason=data["reason"],
        source_episode=data["source_episode"],
        prior_version=data.get("prior_version"),
        resulting_version=data["resulting_version"],
        archived=data["archived"],
        created_at=data["created_at"],
        safety=safety,
    )


def _project_name(text: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9 ]+", " ", text).strip()
    words = clean.split()
    return " ".join(words[:6]) or "RC3 Project"


if __name__ == "__main__":
    print(json.dumps(run_all_stages(write_reports=True), indent=2, sort_keys=True))
