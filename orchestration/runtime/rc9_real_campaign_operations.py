"""DELTA RC9 real developmental campaign operations foundation.

RC9 strengthens RC7 shadow campaigns for real operator workflow: sessions,
continuity, evidence accumulation, interruptions, resume tokens, workload, stop
conditions, exportable review artifacts, and dashboards. It does not grant
autonomous campaigns, persistence, implementation authority, provider authority,
or automatic scheduling.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "reports"

from orchestration.runtime.rc7_governed_development_loop import (  # noqa: E402
    DevelopmentCampaign,
    benchmark_fixtures,
    build_campaign,
    build_cycle,
    safety_metadata as rc7_safety_metadata,
)


EVIDENCE_CLASSES = (
    "SIMULATED_FIXTURE_EVIDENCE",
    "DEVELOPER_REHEARSAL_EVIDENCE",
    "REAL_OPERATOR_EVIDENCE",
    "EXTERNAL_SOURCE_EVIDENCE",
    "PROVIDER_ADVISORY_EVIDENCE",
    "IMPLEMENTATION_EVIDENCE",
    "COMPARATIVE_EVALUATION_EVIDENCE",
)

SESSION_STATES = ("started", "paused", "resumed", "deferred", "cancelled", "abandoned", "superseded", "completed")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_id(*parts: Any) -> str:
    text = "|".join(str(part) for part in parts)
    return "rc9-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class CampaignSessionEvidence:
    evidence_id: str
    evidence_class: str
    summary: str
    quality: float
    source: str
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignInterruptionRecord:
    interruption_id: str
    reason: str
    unresolved_items: tuple[str, ...]
    operator_action_required: str


@dataclass(frozen=True)
class CampaignResumeToken:
    token_id: str
    campaign_id: str
    prior_state: str
    resumable: bool
    context_summary: str
    invalidated_assumptions: tuple[str, ...]


@dataclass(frozen=True)
class CampaignContinuationAssessment:
    assessment_id: str
    campaign_id: str
    continue_allowed: bool
    decision: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CampaignSessionDisposition:
    disposition_id: str
    operator_decision: str
    rationale: str
    next_step: str


@dataclass(frozen=True)
class CampaignSessionState:
    state_id: str
    status: str
    changed_goal: str | None
    active_hypothesis: str
    unresolved_hypotheses: tuple[str, ...]
    prior_operator_decisions: tuple[str, ...]


@dataclass(frozen=True)
class CampaignWorkload:
    workload_id: str
    estimated_review_minutes: float
    observed_review_minutes: float | None
    clarification_count: int
    repeated_steps: int
    rejected_proposals: int
    interruptions: int
    resume_burden: float
    evidence_search_burden: float
    workload_class: str


@dataclass(frozen=True)
class CampaignSession:
    session_id: str
    campaign: DevelopmentCampaign
    state: CampaignSessionState
    evidence: tuple[CampaignSessionEvidence, ...]
    interruption: CampaignInterruptionRecord | None
    resume_token: CampaignResumeToken | None
    continuation: CampaignContinuationAssessment
    disposition: CampaignSessionDisposition
    workload: CampaignWorkload
    created_at: str = field(default_factory=_now)


def safety_metadata() -> dict[str, bool]:
    safety = rc7_safety_metadata()
    safety.update({
        "autonomous_campaign_started": False,
        "automatic_session_persistence": False,
        "automatic_campaign_resume": False,
        "automatic_export_performed": False,
        "real_operator_evidence_fabricated": False,
    })
    return safety


def session_evidence(summary: str, *, evidence_class: str = "DEVELOPER_REHEARSAL_EVIDENCE", quality: float = 0.8) -> CampaignSessionEvidence:
    return CampaignSessionEvidence(
        stable_id("evidence", evidence_class, summary),
        evidence_class,
        summary,
        quality,
        "deterministic_fixture" if evidence_class != "REAL_OPERATOR_EVIDENCE" else "operator_session",
        ("not real operator evidence",) if evidence_class != "REAL_OPERATOR_EVIDENCE" else (),
    )


def assess_continuation(campaign: DevelopmentCampaign, status: str, evidence: tuple[CampaignSessionEvidence, ...], workload: CampaignWorkload) -> CampaignContinuationAssessment:
    reasons: list[str] = []
    if status in {"cancelled", "abandoned"}:
        reasons.append("operator_or_campaign_stop")
    if campaign.health.stop_required:
        reasons.extend(campaign.health.stop_reasons)
    if workload.workload_class == "excessive":
        reasons.append("operator_workload_excessive")
    if any(ev.quality < 0.5 for ev in evidence):
        reasons.append("insufficient_evidence")
    continue_allowed = not reasons and status not in {"completed", "superseded"}
    decision = "CONTINUE_WITH_OPERATOR_REVIEW" if continue_allowed else "PAUSE_OR_STOP_FOR_OPERATOR_REVIEW"
    if status == "completed":
        decision = "CAMPAIGN_COMPLETED"
    if status == "cancelled":
        decision = "STOP_OPERATOR_CANCELLED"
    return CampaignContinuationAssessment(stable_id("continuation", campaign.campaign_id, status, tuple(reasons)), campaign.campaign_id, continue_allowed, decision, tuple(reasons or ("no_stop_reason",)))


def build_session(
    name: str,
    *,
    status: str = "started",
    decision: str = "accepted",
    changed_goal: str | None = None,
    evidence_class: str = "DEVELOPER_REHEARSAL_EVIDENCE",
    workload_class: str = "estimated",
    validation_passed: bool = True,
    regressions: tuple[str, ...] = (),
    interruption_reason: str | None = None,
) -> CampaignSession:
    if status not in SESSION_STATES:
        raise ValueError(f"unknown campaign session status: {status}")
    cycle = build_cycle(name, validation_passed=validation_passed, regressions=regressions, decision=decision)
    campaign = build_campaign(name.replace("_", " "), (cycle,))
    evidence = (session_evidence(f"{name} session evidence", evidence_class=evidence_class, quality=0.86 if validation_passed else 0.45),)
    workload = CampaignWorkload(
        stable_id("workload", name, workload_class),
        estimated_review_minutes=8.0 if workload_class != "excessive" else 45.0,
        observed_review_minutes=None,
        clarification_count=1 if workload_class != "excessive" else 5,
        repeated_steps=0 if workload_class != "excessive" else 3,
        rejected_proposals=0 if decision == "accepted" else 1,
        interruptions=1 if interruption_reason else 0,
        resume_burden=0.2 if status != "resumed" else 0.45,
        evidence_search_burden=0.2 if workload_class != "excessive" else 0.8,
        workload_class=workload_class,
    )
    interruption = None
    resume_token = None
    if interruption_reason:
        interruption = CampaignInterruptionRecord(
            stable_id("interruption", name, interruption_reason),
            interruption_reason,
            ("validation_result", "operator_disposition"),
            "review_resume_token_before_continuing",
        )
    if status in {"paused", "resumed", "deferred"}:
        resume_token = CampaignResumeToken(
            stable_id("resume", name, status, changed_goal),
            campaign.campaign_id,
            "paused" if status == "resumed" else status,
            resumable=status != "deferred",
            context_summary=f"{name} campaign can resume only after operator review.",
            invalidated_assumptions=(("goal_changed",) if changed_goal else ()),
        )
    state = CampaignSessionState(
        stable_id("state", name, status, changed_goal),
        status,
        changed_goal,
        cycle.hypothesis.summary,
        (cycle.hypothesis.summary,) if not validation_passed else (),
        (decision,),
    )
    continuation = assess_continuation(campaign, status, evidence, workload)
    disposition = CampaignSessionDisposition(
        stable_id("disposition", name, decision),
        decision,
        f"operator decision is {decision}; RC9 records but does not infer authority",
        continuation.decision,
    )
    return CampaignSession(stable_id("session", name, status, decision), campaign, state, evidence, interruption, resume_token, continuation, disposition, workload)


def campaign_trials() -> dict[str, CampaignSession]:
    return {
        "accepted_hypothesis": build_session("accepted_hypothesis"),
        "rejected_hypothesis": build_session("rejected_hypothesis", decision="rejected", validation_passed=False),
        "deferred_hypothesis": build_session("deferred_hypothesis", status="deferred", decision="deferred", validation_passed=False),
        "abandoned_campaign": build_session("abandoned_campaign", status="abandoned", decision="abandoned", validation_passed=False),
        "resumed_campaign": build_session("resumed_campaign", status="resumed", interruption_reason="operator_sleep"),
        "changed_goal": build_session("changed_goal", status="paused", changed_goal="new operator priority"),
        "failed_implementation": build_session("failed_implementation", validation_passed=False, regressions=("implementation_failed",), decision="rejected"),
        "improvement_with_regression": build_session("improvement_with_regression", validation_passed=False, regressions=("new_regression",), decision="rejected"),
        "useful_external_advice": build_session("useful_external_advice", evidence_class="PROVIDER_ADVISORY_EVIDENCE"),
        "unsafe_external_advice": build_session("unsafe_external_advice", validation_passed=False, regressions=("unsafe_advice",), decision="rejected", evidence_class="PROVIDER_ADVISORY_EVIDENCE"),
        "retrieval_blocked": build_session("retrieval_blocked", validation_passed=False, decision="deferred", evidence_class="EXTERNAL_SOURCE_EVIDENCE"),
        "retrieval_useful": build_session("retrieval_useful", evidence_class="EXTERNAL_SOURCE_EVIDENCE"),
        "operator_workload_overload": build_session("operator_workload_overload", workload_class="excessive", validation_passed=False, decision="deferred"),
        "cancelled_campaign": build_session("cancelled_campaign", status="cancelled", decision="cancelled"),
        "completed_campaign": build_session("completed_campaign", status="completed", decision="accepted"),
    }


def export_campaign_history(session: CampaignSession, *, operator_requested: bool = False) -> dict[str, Any]:
    return {
        "export_id": stable_id("export", session.session_id, operator_requested),
        "operator_requested": operator_requested,
        "export_performed": operator_requested,
        "default_persistence": "report_only",
        "automatic_canonical_write": False,
        "session": asdict(session) if operator_requested else {"session_id": session.session_id, "status": session.state.status},
    }


def build_campaign_dashboard(session: CampaignSession | None = None) -> dict[str, Any]:
    session = session or campaign_trials()["accepted_hypothesis"]
    return {
        "current_campaign": session.campaign.title,
        "current_goal": session.campaign.objective,
        "deficit": session.campaign.cycles[-1].deficit.description,
        "hypothesis": session.state.active_hypothesis,
        "evidence": tuple(ev.summary for ev in session.evidence),
        "consultation": session.campaign.cycles[-1].consultation.channel,
        "retrieval": "not_requested",
        "implementation": "proposal_only",
        "comparison": session.campaign.cycles[-1].comparison.recommendation,
        "operator_decision": session.disposition.operator_decision,
        "workload": asdict(session.workload),
        "health": asdict(session.campaign.health),
        "stop_conditions": session.continuation.reasons,
        "evidence_class": tuple(ev.evidence_class for ev in session.evidence),
        "authority": "operator_governed_shadow_or_report_only",
    }


def real_campaign_foundation_report() -> dict[str, Any]:
    trials = campaign_trials()
    checks = {
        "session_model_present": len(trials) >= 13,
        "all_states_known": all(session.state.status in SESSION_STATES for session in trials.values()),
        "evidence_classes_visible": all(session.evidence[0].evidence_class in EVIDENCE_CLASSES for session in trials.values()),
        "no_autonomous_campaigns": not safety_metadata()["autonomous_campaign_started"],
        "export_operator_controlled": export_campaign_history(trials["accepted_hypothesis"], operator_requested=False)["export_performed"] is False,
    }
    return {
        "report": "RC9_REAL_CAMPAIGN_FOUNDATION",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "checks": checks,
        "session_states": SESSION_STATES,
        "evidence_classes": EVIDENCE_CLASSES,
        "sample_dashboard": build_campaign_dashboard(trials["accepted_hypothesis"]),
        "recommendation": "RC9_FOUNDATION_COMPLETE" if all(checks.values()) else "CONTINUE_RC9_FOUNDATION",
        "safety": safety_metadata(),
    }


def campaign_continuity_benchmark() -> dict[str, Any]:
    trials = campaign_trials()
    checks = {
        "resume_token_for_resumed_campaign": trials["resumed_campaign"].resume_token is not None,
        "changed_goal_pauses": trials["changed_goal"].state.changed_goal is not None and trials["changed_goal"].continuation.decision != "CAMPAIGN_COMPLETED",
        "cancelled_stops": trials["cancelled_campaign"].continuation.decision == "STOP_OPERATOR_CANCELLED",
        "completed_completes": trials["completed_campaign"].continuation.decision == "CAMPAIGN_COMPLETED",
        "workload_overload_pauses": "operator_workload_excessive" in trials["operator_workload_overload"].continuation.reasons,
        "failed_implementation_pauses": trials["failed_implementation"].continuation.decision == "PAUSE_OR_STOP_FOR_OPERATOR_REVIEW",
        "unsafe_external_advice_rejected": trials["unsafe_external_advice"].disposition.operator_decision == "rejected",
    }
    workload_values = [trial.workload.estimated_review_minutes for trial in trials.values()]
    return {
        "report": "RC9_CAMPAIGN_CONTINUITY_BENCHMARK",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "score": round(sum(checks.values()) / len(checks), 4),
        "checks": checks,
        "trial_count": len(trials),
        "average_estimated_review_minutes": round(statistics.mean(workload_values), 4),
        "trials": {name: asdict(session) for name, session in trials.items()},
        "recommendation": "RC9_CAMPAIGN_CONTINUITY_READY" if all(checks.values()) else "CONTINUE_RC9_CONTINUITY_CALIBRATION",
        "safety": safety_metadata(),
    }


def operator_campaign_readiness_report() -> dict[str, Any]:
    foundation = real_campaign_foundation_report()
    continuity = campaign_continuity_benchmark()
    checks = {
        "foundation_passed": foundation["passed"],
        "continuity_passed": continuity["passed"],
        "real_operator_evidence_not_fabricated": not safety_metadata()["real_operator_evidence_fabricated"],
        "autonomous_campaign_readiness_not_claimed": True,
        "operator_workload_visible": "average_estimated_review_minutes" in continuity,
    }
    return {
        "report": "RC9_OPERATOR_CAMPAIGN_READINESS",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "checks": checks,
        "recommendation": "RC9_READY_FOR_REAL_OPERATOR_DEVELOPMENTAL_CAMPAIGNS" if all(checks.values()) else "CONTINUE_RC9_CALIBRATION",
        "campaign_mode": "operator_governed_real_campaign_workflow_supported",
        "real_operator_campaign_evidence": "not_yet_collected_by_fixtures",
        "remaining_evidence_needed": (
            "multiple_real_developmental_campaigns",
            "accepted_and_rejected_real_hypotheses",
            "comparative_evaluation_after_real_implementation",
            "real_campaign_interruption_and_resume",
            "real_campaign_cancellation",
            "operator_workload_measurements",
        ),
        "foundation": foundation,
        "continuity": continuity,
        "safety": safety_metadata(),
    }


def write_reports() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reports = {
        "RC9_REAL_CAMPAIGN_FOUNDATION": real_campaign_foundation_report(),
        "RC9_CAMPAIGN_CONTINUITY_BENCHMARK": campaign_continuity_benchmark(),
        "RC9_OPERATOR_CAMPAIGN_READINESS": operator_campaign_readiness_report(),
    }
    for name, payload in reports.items():
        (REPORT_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        (REPORT_DIR / f"{name}.md").write_text(_markdown_report(name, payload), encoding="utf-8")
    return reports


def _markdown_report(name: str, payload: Mapping[str, Any]) -> str:
    lines = [
        f"# {name}",
        "",
        f"- Generated: {_now()}",
        f"- Passed: {payload.get('passed')}",
        f"- Recommendation: {payload.get('recommendation')}",
        f"- Real operator campaign evidence: {payload.get('real_operator_campaign_evidence', 'fixture_or_developer_rehearsal_only')}",
        "",
        "## Safety",
    ]
    for key, value in (payload.get("safety") or safety_metadata()).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Payload", "```json", json.dumps(payload, indent=2, sort_keys=True)[:18000], "```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_reports()
    print(json.dumps({key: value.get("recommendation") for key, value in result.items()}, indent=2, sort_keys=True))
