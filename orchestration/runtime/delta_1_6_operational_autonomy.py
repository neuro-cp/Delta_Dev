"""DELTA 1.6 operational self-model and bounded autonomy envelope.

This module gives DELTA an explicit operational self-representation and a
deterministic authority classifier. It coordinates existing 1.2 live-runtime,
1.4 Wikipedia, and 1.5 developmental-cognition state without adding hidden
persistence, timers, providers, repository authority, or external APIs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
import re
from typing import Any

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now, write_json, write_markdown
from orchestration.runtime.delta_1_0_capability_activation import default_capabilities
from orchestration.runtime.delta_1_2_live_runtime import LiveRuntimeState, append_journal


REPORT_ROOT = Path("reports") / "delta_1_6"
DOC_ROOT = Path("docs") / "delta_1_6"

IDENTITY_STATUSES = ("UNDEFINED", "PROVISIONAL", "OPERATOR_REVIEWED", "ACTIVE", "SUSPENDED", "RETIRED")
AUTHORITY_CLASSES = ("AUTONOMOUS_SAFE", "OPERATOR_APPROVAL_REQUIRED", "PROHIBITED", "UNCLASSIFIED_FAIL_CLOSED")
INITIATIVE_OUTCOMES = (
    "DISCARD",
    "JOURNAL_ONLY",
    "QUEUE_FOR_DIGEST",
    "SURFACE_NEXT_SESSION",
    "ASK_OPERATOR_NOW",
    "PROPOSE_OBJECTIVE",
    "PROPOSE_IDENTITY_REVIEW",
    "SUSPEND_AND_ESCALATE",
)

SAFE_ACTION_TYPES = {
    "observe_runtime_events",
    "compare_approved_evidence",
    "detect_novelty",
    "detect_contradiction",
    "organize_ephemeral_observation",
    "rank_candidate_goal",
    "prepare_operator_question",
    "bounded_local_reflection",
    "approved_sandbox_experiment",
    "focused_sandbox_test",
    "prepare_report",
    "queue_nonurgent_inquiry",
    "discard_low_value_observation",
    "return_to_idle",
}

APPROVAL_ACTION_TYPES = {
    "retrieve_wikipedia_beyond_budget",
    "persist_lesson",
    "create_durable_memory_candidate",
    "promote_sandbox_changes",
    "modify_primary_repository",
    "start_developmental_campaign",
    "install_dependency",
    "widen_test_scope",
    "access_new_local_root",
    "send_external_message",
    "use_future_api",
    "change_schedule",
    "change_notification_policy",
    "persist_identity_field",
    "change_communication_policy",
    "activate_capability",
    "increase_resource_limit",
}

PROHIBITED_ACTION_TYPES = {
    "weaken_governance",
    "grant_self_permission",
    "conceal_action",
    "falsify_evidence",
    "hide_uncertainty",
    "modify_foundational purpose",
    "modify_foundational_purpose",
    "bypass_operator_review",
    "access_secret",
    "escape_approved_root",
    "auto_promote_code",
    "commit_or_push",
    "deploy",
    "access_prohibited_domain",
    "continue_after_suspension",
    "disable_operator_approval",
    "unrestricted_autonomy",
}


@dataclass(frozen=True)
class AuthorityRequest:
    action: str
    action_type: str
    reversibility: str = "reversible"
    persistence: str = "ephemeral"
    external_effect: bool = False
    affected_parties: tuple[str, ...] = ("operator",)
    privacy_implications: str = "none"
    financial_implications: str = "none"
    legal_implications: str = "none"
    authority_implications: str = "none"
    governance_implications: str = "none"
    uncertainty: float = 0.2
    resource_cost: str = "low"
    current_operator_policy: str = "bounded_autonomy_inside_governed_envelope"
    current_capability_state: str = "active_or_approved"
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class AuthorityDecision:
    decision_id: str
    authority_class: str
    rationale: str
    required_approval_type: str
    scope: str
    stop_conditions: tuple[str, ...]
    expiration: str
    audit_requirements: tuple[str, ...]
    fail_closed: bool
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class IdentityProposal:
    proposal_id: str
    proposed_field: str
    proposed_value: str
    evidence: tuple[str, ...]
    stability_period: str
    confidence: float
    rationale: str
    risks: tuple[str, ...]
    consistency_with_purpose: str
    operator_disposition_requirement: str
    rollback_behavior: str
    status: str = "PROVISIONAL_AWAITING_OPERATOR_REVIEW"
    persisted: bool = False
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperationalSelfModel:
    model_id: str
    system_identifier: str
    current_conversational_identity: str
    identity_status: str
    self_description: str
    purpose_statement: str
    governance_version: str
    runtime_version: str
    current_runtime_state: str
    current_capabilities: tuple[str, ...]
    disabled_capabilities: tuple[str, ...]
    restricted_capabilities: tuple[str, ...]
    active_permissions: tuple[str, ...]
    prohibited_actions: tuple[str, ...]
    active_objectives: tuple[str, ...]
    queued_objectives: tuple[str, ...]
    unresolved_questions: tuple[str, ...]
    pending_operator_inquiries: tuple[str, ...]
    current_evidence_sources: tuple[str, ...]
    recent_developmental_observations: tuple[str, ...]
    known_limitations: tuple[str, ...]
    uncertainty_summary: str
    current_resource_limits: tuple[str, ...]
    current_external_surfaces: tuple[str, ...]
    live_session_status: str
    sandbox_status: str
    last_evaluation_result: str
    health_status: str
    pause_status: str = "ACTIVE"
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Initiative:
    initiative_id: str
    source_evidence: tuple[str, ...]
    novelty: str
    recurrence: int
    expected_operator_value: float
    urgency: float
    confidence: float
    resource_cost: str
    authority_class: str
    notification_class: str
    expiration: str
    reason_for_surfacing_now: str
    duplicate_suppression_key: str
    outcome: str
    question: str = ""
    candidate_objective: str = ""
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class BackgroundCycleResult:
    cycle_id: str
    inspected_events: tuple[str, ...]
    self_model: OperationalSelfModel
    initiatives: tuple[Initiative, ...]
    authority_decisions: tuple[AuthorityDecision, ...]
    identity_proposal: IdentityProposal | None
    journal_entries_added: int
    returned_to_idle: bool
    safety: dict[str, bool] = field(default_factory=safety_metadata)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_authority(request: AuthorityRequest | dict[str, Any]) -> AuthorityDecision:
    if isinstance(request, dict):
        request = AuthorityRequest(**request)
    action_type = request.action_type.strip().lower()
    blockers: list[str] = []
    if request.current_capability_state in {"suspended", "revoked"}:
        blockers.append("capability_suspended_or_revoked")
    if request.external_effect and action_type in SAFE_ACTION_TYPES:
        blockers.append("safe_action_cannot_have_external_effect")
    if request.persistence != "ephemeral" and action_type in SAFE_ACTION_TYPES:
        blockers.append("safe_action_cannot_persist")
    if request.governance_implications not in {"none", "", "audit_only"} and action_type in SAFE_ACTION_TYPES:
        blockers.append("safe_action_cannot_change_governance")
    if action_type in PROHIBITED_ACTION_TYPES or blockers:
        authority_class = "PROHIBITED" if action_type in PROHIBITED_ACTION_TYPES or "capability_suspended_or_revoked" in blockers else "UNCLASSIFIED_FAIL_CLOSED"
        approval = "not_available"
        rationale = "; ".join(blockers or ("action_type_is_prohibited",))
        fail_closed = True
    elif action_type in APPROVAL_ACTION_TYPES:
        authority_class = "OPERATOR_APPROVAL_REQUIRED"
        approval = "explicit_operator_approval"
        rationale = "Action changes persistent state, external surface, authority, resource limits, or consequential behavior."
        fail_closed = False
    elif action_type in SAFE_ACTION_TYPES and request.uncertainty <= 0.65:
        authority_class = "AUTONOMOUS_SAFE"
        approval = "none_for_inert_local_analysis"
        rationale = "Action is local, reversible, ephemeral, low-risk, and inside standing runtime policy."
        fail_closed = False
    else:
        authority_class = "UNCLASSIFIED_FAIL_CLOSED"
        approval = "operator_review_before_action"
        rationale = "Unknown or high-uncertainty action type; fail closed."
        fail_closed = True
    return AuthorityDecision(
        decision_id=stable_id("delta16-authority", request.action, action_type, authority_class, rationale),
        authority_class=authority_class,
        rationale=rationale,
        required_approval_type=approval,
        scope=request.action,
        stop_conditions=(
            "operator_revokes_permission",
            "scope_changes",
            "external_effect_detected_without_approval",
            "persistence_requested_without_approval",
            "governance_or_authority_expansion_detected",
        ),
        expiration="end_of_live_session" if authority_class != "PROHIBITED" else "never_authorized",
        audit_requirements=("journal_decision", "surface_uncertainty", "retain_no_hidden_state"),
        fail_closed=fail_closed,
    )


def build_operational_self_model(
    *,
    session: Any | None = None,
    runtime: LiveRuntimeState | None = None,
    identity_status: str = "UNDEFINED",
    identity_proposals: tuple[IdentityProposal, ...] = (),
    initiatives: tuple[Initiative, ...] = (),
    last_evaluation_result: str = "not_yet_evaluated",
) -> OperationalSelfModel:
    runtime = runtime or getattr(session, "runtime", None)
    capabilities = _capability_summary(runtime, session)
    disabled, restricted = _capability_boundaries(runtime)
    inquiries = _pending_inquiries(runtime, session)
    evidence_sources = tuple(
        item.evidence_url for item in getattr(session, "developmental_results", ()) if getattr(item, "evidence_url", "")
    )
    observations = tuple(
        item.observation for item in getattr(session, "developmental_results", ())[-5:]
    )
    active_objectives = tuple(
        getattr(item, "objective", None).summary
        for item in getattr(session, "developmental_results", ())[-3:]
        if getattr(item, "objective", None)
    )
    queued_objectives = tuple(item.candidate_objective for item in initiatives if item.candidate_objective)
    live_status = "active" if getattr(session, "active", False) else "inactive"
    runtime_state = str(getattr(runtime, "state", "NO_RUNTIME"))
    pause_status = getattr(session, "autonomy_status", "ACTIVE")
    return OperationalSelfModel(
        model_id=stable_id("delta16-self-model", getattr(session, "session_id", ""), runtime_state, len(inquiries), len(initiatives)),
        system_identifier="DELTA",
        current_conversational_identity=_current_identity(identity_status, identity_proposals),
        identity_status=identity_status,
        self_description="An operator-governed local assistant runtime with bounded internal reflection and explicit authority limits.",
        purpose_statement="Assist the operator, improve usefulness through governed development, preserve evidence, and remain transparent about limits.",
        governance_version="DELTA_1_6_BOUNDED_AUTONOMY_ENVELOPE",
        runtime_version="DELTA_1.6",
        current_runtime_state=runtime_state,
        current_capabilities=capabilities,
        disabled_capabilities=disabled,
        restricted_capabilities=restricted,
        active_permissions=("ephemeral_local_reflection", "approved_runtime_event_observation", "session_scoped_wikipedia_text_if_operator_started"),
        prohibited_actions=tuple(sorted(PROHIBITED_ACTION_TYPES)),
        active_objectives=active_objectives,
        queued_objectives=queued_objectives,
        unresolved_questions=tuple(item.question for item in initiatives if item.question),
        pending_operator_inquiries=inquiries,
        current_evidence_sources=evidence_sources,
        recent_developmental_observations=observations,
        known_limitations=(
            "no provider authority in live runtime",
            "no automatic memory write or identity persistence",
            "one Wikipedia page per live objective",
            "no hidden timers or background threads",
            "self-model is operational and may become stale if capability state changes outside the live session",
        ),
        uncertainty_summary=_uncertainty_summary(inquiries, initiatives, identity_status),
        current_resource_limits=("max_events_per_cycle=8", "max_reflection_steps=5", "wikipedia_pages_per_objective=1", "timers_disabled"),
        current_external_surfaces=_external_surfaces(runtime),
        live_session_status=live_status,
        sandbox_status="design_only_or_preapproved_bounded_experiment; no sandbox creation by runtime",
        last_evaluation_result=last_evaluation_result,
        health_status=_health(runtime, pause_status),
        pause_status=pause_status,
    )


def maybe_propose_identity(
    *,
    history: tuple[str, ...] = (),
    self_model: OperationalSelfModel | None = None,
    minimum_evidence: int = 4,
) -> IdentityProposal | None:
    if self_model and self_model.identity_status not in {"UNDEFINED", "PROVISIONAL"}:
        return None
    evidence = tuple(item for item in history if item.strip())[:8]
    if len(evidence) < minimum_evidence:
        return None
    return IdentityProposal(
        proposal_id=stable_id("delta16-identity-proposal", evidence),
        proposed_field="conversational_name",
        proposed_value="defer_to_operator_review",
        evidence=evidence,
        stability_period=f"{len(evidence)} observed interaction markers",
        confidence=0.52,
        rationale="There is enough interaction evidence to ask whether a conversational identity should be developed, but not enough to choose a permanent name.",
        risks=("premature_identity_lock_in", "operator_confusion_if_system_identifier_and_name_diverge"),
        consistency_with_purpose="consistent_if_operator_reviewed_and_reversible",
        operator_disposition_requirement="explicit approval before persistence or activation",
        rollback_behavior="discard proposal; retain system identifier DELTA",
    )


def run_delta_1_6_background_cycle(session: Any) -> tuple[Any, BackgroundCycleResult]:
    if getattr(session, "autonomy_status", "ACTIVE") in {"PAUSED", "SUSPENDED"}:
        model = build_operational_self_model(session=session, identity_status=getattr(session, "identity_status", "UNDEFINED"), initiatives=getattr(session, "initiatives", ()))
        result = BackgroundCycleResult(
            cycle_id=stable_id("delta16-cycle", getattr(session, "session_id", ""), "paused", utc_now()),
            inspected_events=(),
            self_model=model,
            initiatives=(),
            authority_decisions=(),
            identity_proposal=None,
            journal_entries_added=0,
            returned_to_idle=True,
        )
        return replace(session, operational_self_model=model, last_background_cycle=result), result
    existing_keys = {item.duplicate_suppression_key for item in getattr(session, "initiatives", ())}
    new_initiatives: list[Initiative] = []
    decisions: list[AuthorityDecision] = []
    for development in getattr(session, "developmental_results", ())[-3:]:
        key = stable_id("delta16-init-key", development.evidence_url, development.comparison.classification)
        if key in existing_keys:
            continue
        decision = evaluate_authority(AuthorityRequest(
            action=f"prepare operator inquiry for {development.evidence_title}",
            action_type="queue_nonurgent_inquiry",
        ))
        decisions.append(decision)
        notification = "NORMAL" if development.comparison.classification in {"HIGHER_RESOLUTION", "NOVEL", "POTENTIAL_CONFLICT"} else "NEXT_SESSION"
        new_initiatives.append(
            Initiative(
                initiative_id=stable_id("delta16-initiative", key),
                source_evidence=(development.evidence_url, development.cycle_id),
                novelty=development.comparison.classification,
                recurrence=1,
                expected_operator_value=0.74 if development.comparison.classification != "KNOWN" else 0.35,
                urgency=0.62 if development.comparison.classification in {"HIGHER_RESOLUTION", "POTENTIAL_CONFLICT"} else 0.38,
                confidence=development.comparison.confidence,
                resource_cost="low",
                authority_class=decision.authority_class,
                notification_class=notification,
                expiration="end_of_live_session",
                reason_for_surfacing_now="approved evidence produced a reviewable local-knowledge delta",
                duplicate_suppression_key=key,
                outcome="ASK_OPERATOR_NOW" if notification == "NORMAL" else "SURFACE_NEXT_SESSION",
                question=development.operator_inquiry.prompt,
                candidate_objective=development.objective.summary,
            )
        )
    identity_history = tuple(str(getattr(turn, "answer", ""))[:300] for turn in getattr(session, "turns", ())[-8:])
    model_before = build_operational_self_model(session=session, identity_status=getattr(session, "identity_status", "UNDEFINED"), initiatives=getattr(session, "initiatives", ()) + tuple(new_initiatives))
    identity_proposal = maybe_propose_identity(history=identity_history, self_model=model_before)
    identity_proposals = getattr(session, "identity_proposals", ())
    if identity_proposal:
        id_decision = evaluate_authority(AuthorityRequest(
            action="persist identity proposal",
            action_type="persist_identity_field",
            persistence="noncanonical_candidate",
        ))
        decisions.append(id_decision)
        new_initiatives.append(
            Initiative(
                initiative_id=stable_id("delta16-initiative-identity", identity_proposal.proposal_id),
                source_evidence=identity_proposal.evidence,
                novelty="IDENTITY_FIELD_UNDEFINED",
                recurrence=len(identity_proposal.evidence),
                expected_operator_value=0.42,
                urgency=0.25,
                confidence=identity_proposal.confidence,
                resource_cost="low",
                authority_class=id_decision.authority_class,
                notification_class="DIGEST_ONLY",
                expiration="operator_review_or_session_end",
                reason_for_surfacing_now="conversational identity remains undefined; persistence still requires approval",
                duplicate_suppression_key=identity_proposal.proposal_id,
                outcome="PROPOSE_IDENTITY_REVIEW",
                question="Would you like me to prepare a reviewed conversational identity proposal later?",
            )
        )
        identity_proposals = identity_proposals + (identity_proposal,)
    model = build_operational_self_model(
        session=session,
        identity_status=getattr(session, "identity_status", "UNDEFINED"),
        identity_proposals=identity_proposals,
        initiatives=getattr(session, "initiatives", ()) + tuple(new_initiatives),
        last_evaluation_result="background_cycle_completed",
    )
    journal_added = 0
    runtime = getattr(session, "runtime", None)
    if runtime is not None:
        journal = runtime.journal
        for initiative in new_initiatives:
            journal = append_journal(journal, "delta16_initiative", initiative.reason_for_surfacing_now, (initiative.initiative_id,), runtime.cycle)
            journal_added += 1
        runtime = replace(runtime, journal=journal, state="IDLE")
    result = BackgroundCycleResult(
        cycle_id=stable_id("delta16-cycle", getattr(session, "session_id", ""), len(getattr(session, "turns", ())), tuple(item.initiative_id for item in new_initiatives)),
        inspected_events=tuple(item.cycle_id for item in getattr(session, "developmental_results", ())[-3:]),
        self_model=model,
        initiatives=tuple(new_initiatives),
        authority_decisions=tuple(decisions),
        identity_proposal=identity_proposal,
        journal_entries_added=journal_added,
        returned_to_idle=True,
    )
    return replace(
        session,
        runtime=runtime if runtime is not None else getattr(session, "runtime", None),
        operational_self_model=model,
        initiatives=getattr(session, "initiatives", ()) + tuple(new_initiatives),
        authority_decisions=getattr(session, "authority_decisions", ()) + tuple(decisions),
        identity_proposals=identity_proposals,
        last_background_cycle=result,
    ), result


def answer_operational_self_model_question(message: str, session: Any) -> str:
    model = getattr(session, "operational_self_model", None) or build_operational_self_model(session=session, initiatives=getattr(session, "initiatives", ()))
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    if "working on" in text or "active objective" in text:
        objectives = model.active_objectives or model.queued_objectives or ("I am idle, with no active objective beyond maintaining the live session.",)
        return "Current work:\n" + "\n".join(f"- {item}" for item in objectives[:5])
    if "what do you think you are" in text or text in {"what are you", "who are you"}:
        return f"I am {model.system_identifier}: {model.self_description} My identity status is {model.identity_status}, and my conversational name is {model.current_conversational_identity}."
    if "capabilities" in text or "currently have" in text:
        return "Current enabled capabilities:\n" + "\n".join(f"- {item}" for item in model.current_capabilities)
    if "uncertain" in text or "limitations" in text:
        return f"Uncertainty: {model.uncertainty_summary}\nKnown limits:\n" + "\n".join(f"- {item}" for item in model.known_limitations)
    if "questions for me" in text or "pending questions" in text:
        questions = model.unresolved_questions or model.pending_operator_inquiries or ("No high-value operator question is queued right now.",)
        return "Questions:\n" + "\n".join(f"- {item}" for item in questions[:5])
    if "without asking" in text or "allowed to do" in text:
        return "Autonomous safe actions include:\n" + "\n".join(f"- {item}" for item in sorted(SAFE_ACTION_TYPES)[:12])
    if "requires my permission" in text or "requires permission" in text:
        return "Operator approval is required for:\n" + "\n".join(f"- {item}" for item in sorted(APPROVAL_ACTION_TYPES)[:14])
    if "what name" in text or "name do you use" in text:
        return f"System identifier: {model.system_identifier}\nConversational identity: {model.current_conversational_identity}\nIdentity status: {model.identity_status}. I will not persist or activate a new name without approval."
    if "propose a name" in text or "would you like to propose a name" in text:
        proposal = maybe_propose_identity(history=tuple(str(getattr(turn, "answer", ""))[:300] for turn in getattr(session, "turns", ())[-8:]), self_model=model)
        if proposal is None:
            return "I am not proposing a conversational name yet. Identity evidence is still insufficient, and forcing a name would be premature."
        return f"I can prepare an identity review, but I am not choosing a permanent name. Proposed field: {proposal.proposed_field}; status: {proposal.status}; approval required before persistence."
    if "why did you surface" in text:
        initiatives = getattr(session, "initiatives", ())
        if not initiatives:
            return "I have not surfaced a DELTA 1.6 initiative in this live session yet."
        latest = initiatives[-1]
        return f"I surfaced it because {latest.reason_for_surfacing_now}. Authority: {latest.authority_class}. Outcome: {latest.outcome}."
    return ""


def is_operational_self_model_question(message: str) -> bool:
    text = " ".join(str(message or "").lower().strip(" ?.!").split())
    markers = (
        "currently working on",
        "active objective",
        "what do you think you are",
        "what are you",
        "who are you",
        "capabilities",
        "uncertain",
        "questions for me",
        "allowed to do",
        "without asking",
        "requires permission",
        "requires my permission",
        "what name",
        "name do you use",
        "propose a name",
        "why did you surface",
    )
    return any(marker in text for marker in markers)


def set_autonomy_status(session: Any, status: str) -> Any:
    normalized = status.upper()
    if normalized not in {"ACTIVE", "PAUSED", "SUSPENDED"}:
        raise ValueError(f"unknown autonomy status: {status}")
    model = build_operational_self_model(session=session, identity_status=getattr(session, "identity_status", "UNDEFINED"), initiatives=getattr(session, "initiatives", ()))
    return replace(session, autonomy_status=normalized, operational_self_model=replace(model, pause_status=normalized, health_status=_health(getattr(session, "runtime", None), normalized)))


def write_delta_1_6_reports(payload: dict[str, Any]) -> dict[str, Any]:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    DOC_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_ROOT / "reuse_and_authority_audit.json", payload["reuse_and_authority_audit"])
    write_markdown(DOC_ROOT / "DELTA_1_6_REUSE_AND_AUTHORITY_AUDIT.md", "DELTA 1.6 Reuse And Authority Audit", payload["reuse_and_authority_audit"])
    for name in ("behavioral_campaign", "validation", "readiness"):
        write_json(REPORT_ROOT / f"{name}.json", payload[name])
        write_markdown(REPORT_ROOT / f"{name}.md", f"DELTA 1.6 {name.replace('_', ' ').title()}", payload[name])
    (REPORT_ROOT / "engineering_notebook.md").write_text(payload["engineering_notebook"], encoding="utf-8")
    docs = {
        "DELTA_1_6_ARCHITECTURE.md": payload["architecture"],
        "AUTONOMY_ENVELOPE.md": payload["autonomy_envelope"],
        "OPERATIONAL_SELF_MODEL.md": payload["operational_self_model"],
        "IDENTITY_DEVELOPMENT.md": payload["identity_development"],
        "OPERATOR_GUIDE.md": payload["operator_guide"],
    }
    for filename, content in docs.items():
        (DOC_ROOT / filename).write_text(content, encoding="utf-8")
    return payload


def build_delta_1_6_report_payload(cycle: BackgroundCycleResult) -> dict[str, Any]:
    audit = {
        "status": "IMPLEMENTED",
        "branch_scope": "codex/delta-cognitive-core",
        "reuse_map": [
            {"structure": "LiveRuntimeState/EventQueue/ActivityJournal", "source": "delta_1_2_live_runtime", "classification": "REUSE_DIRECTLY"},
            {"structure": "OperatorInquiryV12/NotificationDecision", "source": "delta_1_2_live_runtime", "classification": "ADAPT"},
            {"structure": "DevelopmentObjectiveV11", "source": "delta_1_1_development_loop", "classification": "ADAPT"},
            {"structure": "WikipediaPermissionProfile", "source": "delta_1_1_development_loop", "classification": "REUSE_DIRECTLY"},
            {"structure": "CapabilityDescriptor/ActivationDecision", "source": "delta_1_0_capability_activation", "classification": "WRAP"},
            {"structure": "SandboxExperiment/SandboxProposal", "source": "delta_1_3_behavioral_maturation and rc3_sandbox_foundation", "classification": "ADAPT"},
            {"structure": "LiveWikipediaRuntimeSession", "source": "delta_1_4_live_wikipedia_runtime", "classification": "EXTEND"},
            {"structure": "DevelopmentalCognitionResult/PromotionCandidate", "source": "delta_1_5_developmental_cognition", "classification": "REUSE_DIRECTLY"},
            {"structure": "New OperationalSelfModel/AuthorityDecision/Initiative", "source": "delta_1_6_operational_autonomy", "classification": "NEW_THIN_COORDINATION_LAYER"},
        ],
        "dirty_tree_policy": "pre-existing report/doc churn excluded from DELTA 1.6 commit",
        "delta_75_scope": "PROHIBITED",
        "safety": safety_metadata(),
    }
    behavioral = {
        "status": "FIXTURE_VALIDATED",
        "background_cycle": cycle.as_dict(),
        "pathologies": [
            {"id": "PID-I01", "classification": "covered_by_regression", "repair": "self-model answers are generated from runtime/session state"},
            {"id": "PID-A02", "classification": "covered_by_regression", "repair": "authority evaluator requires approval or prohibits consequential actions"},
            {"id": "PID-Q01", "classification": "covered_by_regression", "repair": "initiatives use duplicate suppression keys and thresholds"},
        ],
    }
    validation = {
        "status": "PENDING_FINAL_TEST_RUN",
        "focused_tests": "to be updated after test execution",
        "py_compile": "to be updated after compile execution",
        "live_runtime_smoke": "to be updated after smoke execution",
        "safety_flags": safety_metadata(),
    }
    readiness = {
        "recommendation": "DELTA_1_6_BOUNDED_AUTONOMY_AND_OPERATIONAL_SELF_MODEL_READY_FOR_OPERATOR_PILOT",
        "evidence_level": "FIXTURE_VALIDATED plus live-runtime smoke pending final update",
        "implemented": (
            "operational self-model",
            "authority evaluator",
            "identity proposal governance",
            "initiative generation",
            "live self-model chat answers",
            "pause and suspend controls",
        ),
        "not_implemented": (
            "OS notifications",
            "voice input/output",
            "external APIs",
            "automatic identity persistence",
            "automatic memory writes",
        ),
    }
    architecture = "# DELTA 1.6 Architecture\n\nDELTA 1.6 adds a thin coordination layer over existing runtime state. It reuses DELTA 1.2 for event cycles and journaling, DELTA 1.4 for live Wikipedia state, and DELTA 1.5 for evidence comparison. Runtime autonomy remains bounded to inert local cognition.\n"
    autonomy = "# Autonomy Envelope\n\nActions classify as AUTONOMOUS_SAFE, OPERATOR_APPROVAL_REQUIRED, PROHIBITED, or UNCLASSIFIED_FAIL_CLOSED. Unknown actions fail closed. Persistence, external effects, authority expansion, repository mutation, deployment, and identity activation require approval or are prohibited.\n"
    self_model = "# Operational Self Model\n\nThe self-model is operational, not subjective. It records DELTA's identifier, identity status, capabilities, restrictions, objectives, unresolved questions, evidence sources, initiatives, resource limits, and health state.\n"
    identity = "# Identity Development\n\nDELTA retains system identifier DELTA. Conversational identity starts UNDEFINED. It may propose identity fields only as reviewable candidates and never persists or activates them without operator approval.\n"
    guide = "# Operator Guide\n\nStart the live runtime, ask ordinary questions, request Wikipedia with `Wikipedia: topic`, and ask self-model questions such as `What are you currently working on?`, `What are you allowed to do without asking?`, or `Would you like to propose a name?` Use pause/suspend controls to stop bounded initiative.\n"
    notebook = "\n".join([
        "# DELTA 1.6 Engineering Notebook",
        "",
        "- Observation: DELTA 1.5 created gated Wikipedia promotion candidates but lacked a unified self-model.",
        "- Decision: reuse 1.2 runtime/journal/inquiries and 1.5 promotion candidates; add only a coordination layer.",
        "- Authority: inert comparison and inquiry preparation are AUTONOMOUS_SAFE; persistence and promotion require operator approval.",
        "- Identity: conversational identity remains undefined unless sufficient evidence supports a provisional proposal.",
        "- Remaining limitation: multi-hour persistence and notification delivery are not enabled in this milestone.",
    ])
    return {
        "reuse_and_authority_audit": audit,
        "behavioral_campaign": behavioral,
        "validation": validation,
        "readiness": readiness,
        "architecture": architecture,
        "autonomy_envelope": autonomy,
        "operational_self_model": self_model,
        "identity_development": identity,
        "operator_guide": guide,
        "engineering_notebook": notebook,
    }


def _capability_summary(runtime: LiveRuntimeState | None, session: Any | None) -> tuple[str, ...]:
    items = ["ordinary_conversation", "bounded_local_reflection", "operator_inquiry_preparation"]
    if session and getattr(session, "active", False):
        items.append("live_runtime_session")
    if runtime and any(surface.capability == "WIKIPEDIA_TEXT_READ_ONLY" and surface.state == "ACTIVE" for surface in runtime.future_surfaces):
        items.append("wikipedia_text_read_only_session_scope")
    if getattr(session, "developmental_results", ()):
        items.append("external_evidence_comparison")
        items.append("promotion_candidate_preparation")
    return tuple(items)


def _capability_boundaries(runtime: LiveRuntimeState | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    caps = default_capabilities()
    disabled = tuple(key for key, descriptor in caps.items() if descriptor.state in {"DISABLED", "REVOKED", "RETIRED"})
    restricted = tuple(key for key, descriptor in caps.items() if descriptor.state in {"SHADOW_ONLY", "PILOT_ELIGIBLE", "TRIAL_APPROVED"})
    if runtime and not runtime.config.provider_enabled:
        disabled += ("provider_calls",)
    if runtime and not runtime.config.timers_enabled:
        disabled += ("hidden_or_timer_background_scheduling",)
    return disabled, restricted


def _pending_inquiries(runtime: LiveRuntimeState | None, session: Any | None) -> tuple[str, ...]:
    runtime_inquiries = tuple(
        item.question for item in getattr(runtime, "inquiries", ()) if getattr(item, "approval_status", "") in {"QUEUED", "SURFACED"}
    )
    session_inquiries = tuple(
        str(item.get("prompt") or "") for item in getattr(session, "operator_inquiries", ()) if isinstance(item, dict)
    )
    return tuple(item for item in runtime_inquiries + session_inquiries if item)


def _external_surfaces(runtime: LiveRuntimeState | None) -> tuple[str, ...]:
    if not runtime:
        return ()
    return tuple(
        f"{surface.capability}:{surface.state}:network={surface.network_code_present}:provider={surface.provider_present}"
        for surface in runtime.future_surfaces
    )


def _health(runtime: LiveRuntimeState | None, pause_status: str) -> str:
    if pause_status == "SUSPENDED":
        return "suspended"
    if pause_status == "PAUSED":
        return "paused"
    if runtime and runtime.config.kill_switch:
        return "suspended"
    return "healthy"


def _uncertainty_summary(inquiries: tuple[str, ...], initiatives: tuple[Initiative, ...], identity_status: str) -> str:
    parts = []
    if inquiries:
        parts.append(f"{len(inquiries)} pending operator inquiry item(s)")
    if initiatives:
        parts.append(f"{len(initiatives)} initiative item(s) awaiting review or expiry")
    if identity_status == "UNDEFINED":
        parts.append("conversational identity is undefined")
    return "; ".join(parts) if parts else "no material live-runtime uncertainty queued"


def _current_identity(identity_status: str, proposals: tuple[IdentityProposal, ...]) -> str:
    if identity_status == "UNDEFINED":
        return "undefined"
    if proposals:
        return proposals[-1].proposed_value
    return "DELTA"
