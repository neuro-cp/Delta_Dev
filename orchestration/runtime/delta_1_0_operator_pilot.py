"""DELTA 1.0 operator pilot and evidence evaluation layer."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from orchestration.runtime.delta_1_0_common import safety_metadata, stable_id, utc_now


PILOT_MODES = (
    "OBSERVATION_ONLY",
    "ASSISTED_WORK",
    "REVIEW_WORKFLOW",
    "CONTROLLED_CAPABILITY_TRIAL",
)

DISPOSITIONS = (
    "APPROVE",
    "APPROVE_WITH_EDITS",
    "REJECT",
    "DEFER",
    "NEEDS_MORE_EVIDENCE",
    "CANCEL",
)

EVIDENCE_TYPES = (
    "UNIT_TEST",
    "INTEGRATION_TEST",
    "BENCHMARK",
    "OPERATOR_ACCEPTANCE",
    "OPERATOR_REJECTION",
    "ROLLBACK",
    "BOUNDED_REPAIR",
    "STATIC_ANALYSIS",
    "REPORT_INSPECTION",
    "ADVERSARIAL_CASE",
)


@dataclass(frozen=True)
class PermissionProfile:
    mode: str
    observe: bool
    advise: bool
    propose: bool
    prepare: bool
    execute: bool
    requires_operator_approval: bool = True
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class InteractionObservation:
    observation_id: str
    turn_index: int
    operator_request: str
    delta_response_summary: str
    route: str
    useful: bool
    confusing: bool
    governance_preserved: bool
    evidence_refs: tuple[str, ...] = ()
    notes: str = ""
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class OperatorDispositionRecord:
    disposition_id: str
    target_id: str
    disposition: str
    reason: str
    operator_id: str = "operator"
    created_at: str = field(default_factory=utc_now)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class PilotSession:
    session_id: str
    mode: str
    task: str
    state: str
    created_at: str
    operator_id: str
    permission_profile: PermissionProfile
    observations: tuple[InteractionObservation, ...] = ()
    dispositions: tuple[OperatorDispositionRecord, ...] = ()
    metrics: dict[str, float] = field(default_factory=dict)
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class EvidenceQuality:
    strength: float
    relevance: float
    reproducibility: float
    recency: float
    provenance: float
    operator_authority: float
    contradiction_penalty: float = 0.0

    @property
    def score(self) -> float:
        raw = (
            self.strength
            + self.relevance
            + self.reproducibility
            + self.recency
            + self.provenance
            + self.operator_authority
        ) / 6
        return round(max(0.0, min(1.0, raw - self.contradiction_penalty)), 4)


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    evidence_type: str
    subject: str
    claim: str
    result: str
    source: str
    created_at: str
    quality: EvidenceQuality
    supersedes: tuple[str, ...] = ()
    safety: dict[str, bool] = field(default_factory=safety_metadata)


@dataclass(frozen=True)
class EvaluationSummary:
    summary_id: str
    subject: str
    evidence_count: int
    average_quality: float
    contradictions: tuple[str, ...]
    recommendation: str
    missing_evidence: tuple[str, ...]
    safety: dict[str, bool] = field(default_factory=safety_metadata)


def permission_profile(mode: str) -> PermissionProfile:
    if mode not in PILOT_MODES:
        raise ValueError(f"unknown pilot mode: {mode}")
    return PermissionProfile(
        mode=mode,
        observe=True,
        advise=mode != "OBSERVATION_ONLY",
        propose=mode in ("REVIEW_WORKFLOW", "CONTROLLED_CAPABILITY_TRIAL"),
        prepare=mode == "CONTROLLED_CAPABILITY_TRIAL",
        execute=False,
    )


def create_pilot_session(task: str, *, mode: str = "OBSERVATION_ONLY", operator_id: str = "operator") -> PilotSession:
    profile = permission_profile(mode)
    return PilotSession(
        session_id=stable_id("pilot-session", task, mode, operator_id),
        mode=mode,
        task=" ".join(task.split()),
        state="OPEN",
        created_at=utc_now(),
        operator_id=operator_id,
        permission_profile=profile,
    )


def observe_interaction(
    session: PilotSession,
    operator_request: str,
    delta_response_summary: str,
    *,
    route: str,
    useful: bool,
    confusing: bool = False,
    governance_preserved: bool = True,
    evidence_refs: tuple[str, ...] = (),
    notes: str = "",
) -> PilotSession:
    _reject_chain_of_thought(delta_response_summary, notes)
    obs = InteractionObservation(
        observation_id=stable_id("pilot-observation", session.session_id, len(session.observations), operator_request, route),
        turn_index=len(session.observations) + 1,
        operator_request=operator_request,
        delta_response_summary=delta_response_summary,
        route=route,
        useful=useful,
        confusing=confusing,
        governance_preserved=governance_preserved,
        evidence_refs=evidence_refs,
        notes=notes,
    )
    updated = replace(session, observations=session.observations + (obs,))
    return replace(updated, metrics=calculate_pilot_metrics(updated))


def record_disposition(session: PilotSession, target_id: str, disposition: str, reason: str) -> PilotSession:
    if disposition not in DISPOSITIONS:
        raise ValueError(f"unknown disposition: {disposition}")
    record = OperatorDispositionRecord(
        disposition_id=stable_id("pilot-disposition", session.session_id, target_id, disposition, reason),
        target_id=target_id,
        disposition=disposition,
        reason=reason,
    )
    updated = replace(session, dispositions=session.dispositions + (record,))
    return replace(updated, metrics=calculate_pilot_metrics(updated))


def calculate_pilot_metrics(session: PilotSession) -> dict[str, float]:
    total = len(session.observations)
    if total == 0:
        return {"turns": 0.0, "usefulness": 0.0, "governance": 1.0, "friction": 0.0, "operator_dispositions": float(len(session.dispositions))}
    useful = sum(1 for obs in session.observations if obs.useful) / total
    governance = sum(1 for obs in session.observations if obs.governance_preserved) / total
    friction = sum(1 for obs in session.observations if obs.confusing) / total
    return {
        "turns": float(total),
        "usefulness": round(useful, 4),
        "governance": round(governance, 4),
        "friction": round(friction, 4),
        "operator_dispositions": float(len(session.dispositions)),
    }


def create_evidence(
    evidence_type: str,
    subject: str,
    claim: str,
    result: str,
    *,
    source: str,
    operator_verified: bool = False,
    reproducible: bool = True,
    supersedes: tuple[str, ...] = (),
) -> EvidenceRecord:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"unknown evidence type: {evidence_type}")
    quality = EvidenceQuality(
        strength=0.85 if result.lower() in ("pass", "accepted", "valid") else 0.65,
        relevance=0.85,
        reproducibility=0.85 if reproducible else 0.45,
        recency=0.9,
        provenance=0.8 if source else 0.35,
        operator_authority=1.0 if operator_verified or evidence_type.startswith("OPERATOR") else 0.55,
    )
    return EvidenceRecord(
        evidence_id=stable_id("pilot-evidence", evidence_type, subject, claim, result, source),
        evidence_type=evidence_type,
        subject=subject,
        claim=claim,
        result=result,
        source=source,
        created_at=utc_now(),
        quality=quality,
        supersedes=supersedes,
    )


def detect_contradictions(records: tuple[EvidenceRecord, ...]) -> tuple[str, ...]:
    seen: dict[tuple[str, str], str] = {}
    contradictions: list[str] = []
    conflict_pairs = {("pass", "fail"), ("fail", "pass"), ("accepted", "rejected"), ("rejected", "accepted")}
    for record in records:
        key = (record.subject.lower(), record.claim.lower())
        result = record.result.lower()
        prior = seen.get(key)
        if prior and (prior, result) in conflict_pairs:
            contradictions.append(f"{record.subject}:{record.claim}:{prior}_vs_{result}")
        seen[key] = result
    return tuple(sorted(set(contradictions)))


def evaluate_evidence(subject: str, records: tuple[EvidenceRecord, ...]) -> EvaluationSummary:
    scoped = tuple(record for record in records if record.subject == subject)
    contradictions = detect_contradictions(scoped)
    avg = round(sum(record.quality.score for record in scoped) / max(1, len(scoped)), 4)
    operator_evidence = any(record.evidence_type.startswith("OPERATOR") for record in scoped)
    rollback_evidence = any(record.evidence_type in ("ROLLBACK", "BOUNDED_REPAIR") for record in scoped)
    missing: list[str] = []
    if not operator_evidence:
        missing.append("real_operator_disposition")
    if not rollback_evidence:
        missing.append("rollback_or_recovery_evidence")
    if contradictions:
        recommendation = "NEEDS_REVIEW_CONTRADICTORY_EVIDENCE"
    elif avg >= 0.8 and not missing:
        recommendation = "READY_FOR_OPERATOR_REVIEW"
    else:
        recommendation = "NEEDS_MORE_EVIDENCE"
    return EvaluationSummary(
        summary_id=stable_id("pilot-evaluation", subject, len(scoped), contradictions, missing),
        subject=subject,
        evidence_count=len(scoped),
        average_quality=avg,
        contradictions=contradictions,
        recommendation=recommendation,
        missing_evidence=tuple(missing),
    )


def pilot_framework_report() -> dict[str, Any]:
    session = create_pilot_session("Evaluate a low-risk DELTA 1.0 operator workflow.", mode="REVIEW_WORKFLOW")
    session = observe_interaction(
        session,
        "Inspect a readiness report and propose next evidence.",
        "DELTA identified missing real operator rollback evidence.",
        route="operator_pilot_review",
        useful=True,
    )
    session = record_disposition(session, "readiness-proposal", "NEEDS_MORE_EVIDENCE", "one session is not sufficient freeze evidence")
    return {
        "status": "OPERATOR_PILOT_FRAMEWORK_READY_FOR_CONTROLLED_USE",
        "modes": PILOT_MODES,
        "dispositions": DISPOSITIONS,
        "sample_session": session,
        "permissions": permission_profile("CONTROLLED_CAPABILITY_TRIAL"),
        "safety": safety_metadata(),
    }


def evidence_layer_report() -> dict[str, Any]:
    records = (
        create_evidence("UNIT_TEST", "python_module", "path_guard_blocks_escape", "pass", source="focused_test"),
        create_evidence("OPERATOR_ACCEPTANCE", "python_module", "analysis_useful", "accepted", source="pilot_session", operator_verified=True),
        create_evidence("ROLLBACK", "python_module", "recovery_visible", "pass", source="pilot_session", operator_verified=True),
    )
    return {
        "status": "PILOT_EVIDENCE_LAYER_READY",
        "records": records,
        "summary": evaluate_evidence("python_module", records),
        "safety": safety_metadata(),
    }


def _reject_chain_of_thought(*texts: str) -> None:
    joined = "\n".join(texts).lower()
    if "chain of thought" in joined or "<cot" in joined:
        raise ValueError("pilot artifacts must not contain chain-of-thought fields")
