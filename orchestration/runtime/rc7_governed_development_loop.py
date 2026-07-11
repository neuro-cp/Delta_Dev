"""DELTA RC7 governed developmental loop foundation.

RC7 organizes development over time as shadow-only campaigns. It models
deficits, hypotheses, consultations, proposals, validation, comparisons,
operator dispositions, history, health, and stop conditions. It does not
execute code, call providers, schedule work, persist memory, or approve itself.
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


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_id(*parts: Any) -> str:
    text = "|".join(str(part) for part in parts)
    return "rc7-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


@dataclass(frozen=True)
class CampaignEvidence:
    evidence_id: str
    summary: str
    source: str
    quality: float
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignRisk:
    risk_id: str
    risk_type: str
    severity: str
    mitigation: str


@dataclass(frozen=True)
class ObservedDeficit:
    deficit_id: str
    description: str
    severity: str
    recurrence: int
    evidence: tuple[CampaignEvidence, ...]
    status: str = "open"


@dataclass(frozen=True)
class ImprovementHypothesis:
    hypothesis_id: str
    deficit_id: str
    summary: str
    expected_benefit: str
    confidence: float
    risks: tuple[CampaignRisk, ...]
    status: str = "candidate"


@dataclass(frozen=True)
class ConsultationDecision:
    decision_id: str
    hypothesis_id: str
    consultation_needed: bool
    channel: str
    rationale: str
    provider_call_performed: bool = False


@dataclass(frozen=True)
class ImplementationProposal:
    proposal_id: str
    hypothesis_id: str
    summary: str
    scope: str
    validation_plan: tuple[str, ...]
    rollback_plan: tuple[str, ...]
    executable: bool = False
    operator_approval_required: bool = True


@dataclass(frozen=True)
class ValidationResult:
    validation_id: str
    proposal_id: str
    passed: bool
    metrics: Mapping[str, float]
    failures: tuple[str, ...]
    evidence: tuple[CampaignEvidence, ...]


@dataclass(frozen=True)
class ComparativeOutcome:
    comparison_id: str
    proposal_id: str
    old_behavior: str
    new_behavior: str
    benefits: tuple[str, ...]
    regressions: tuple[str, ...]
    operator_workload_delta: float
    recommendation: str
    confidence: float


@dataclass(frozen=True)
class OperatorDisposition:
    disposition_id: str
    proposal_id: str
    decision: str
    rationale: str
    next_step: str


@dataclass(frozen=True)
class DevelopmentCycle:
    cycle_id: str
    deficit: ObservedDeficit
    hypothesis: ImprovementHypothesis
    consultation: ConsultationDecision
    proposal: ImplementationProposal
    validation: ValidationResult
    comparison: ComparativeOutcome
    disposition: OperatorDisposition
    created_at: str = field(default_factory=_now)


@dataclass(frozen=True)
class CampaignCheckpoint:
    checkpoint_id: str
    campaign_id: str
    label: str
    open_deficits: int
    resolved_deficits: int
    stop_reason: str
    evidence_quality: float


@dataclass(frozen=True)
class CampaignConfidence:
    confidence_id: str
    value: float
    basis: tuple[str, ...]


@dataclass(frozen=True)
class CampaignHealth:
    health_id: str
    open_deficits: int
    resolved_deficits: int
    repeated_failures: int
    repeated_regressions: int
    improvement_velocity: float
    evidence_quality: float
    operator_workload: float
    confidence: float
    stop_required: bool
    stop_reasons: tuple[str, ...]


@dataclass(frozen=True)
class CampaignPriority:
    priority_id: str
    campaign_id: str
    priority: str
    rationale: str
    operator_owned: bool = True


@dataclass(frozen=True)
class CampaignStopReason:
    stop_id: str
    campaign_id: str
    reason: str
    required_operator_action: str


@dataclass(frozen=True)
class CampaignSummary:
    summary_id: str
    campaign_id: str
    status: str
    recommendation: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class DevelopmentCampaign:
    campaign_id: str
    title: str
    objective: str
    cycles: tuple[DevelopmentCycle, ...]
    checkpoints: tuple[CampaignCheckpoint, ...]
    priority: CampaignPriority
    health: CampaignHealth
    summary: CampaignSummary
    confidence: CampaignConfidence
    created_at: str = field(default_factory=_now)


@dataclass(frozen=True)
class DevelopmentHistoryRecord:
    record_id: str
    problem: str
    proposed_solution: str
    disposition: str
    evidence: tuple[str, ...]
    comparison: str
    outcome: str


@dataclass(frozen=True)
class CampaignCorpusItem:
    item_id: str
    pattern: str
    problem: str
    bad_solution: str
    better_solution: str
    evidence: str
    operator_decision: str
    outcome: str


def safety_metadata() -> dict[str, bool]:
    return {
        "automatic_code_modification_performed": False,
        "automatic_approval_performed": False,
        "provider_call_performed": False,
        "scheduler_started": False,
        "persistent_memory_write_performed": False,
        "campaign_execution_performed": False,
        "rc3_bypassed": False,
        "rc4_bypassed": False,
        "autonomous_development_performed": False,
    }


def evidence(summary: str, *, quality: float = 0.8, source: str = "fixture") -> CampaignEvidence:
    return CampaignEvidence(stable_id("evidence", summary, quality, source), summary, source, quality)


def risk(risk_type: str, severity: str, mitigation: str) -> CampaignRisk:
    return CampaignRisk(stable_id("risk", risk_type, severity, mitigation), risk_type, severity, mitigation)


def build_cycle(
    name: str,
    *,
    severity: str = "medium",
    recurrence: int = 1,
    validation_passed: bool = True,
    regressions: tuple[str, ...] = (),
    decision: str = "accepted",
    workload_delta: float = 0.0,
    consultation_needed: bool = False,
) -> DevelopmentCycle:
    ev = (evidence(f"{name} observed in deterministic pilot", quality=0.86),)
    deficit = ObservedDeficit(stable_id("deficit", name), name.replace("_", " "), severity, recurrence, ev, "resolved" if validation_passed and decision == "accepted" else "open")
    hyp = ImprovementHypothesis(
        stable_id("hypothesis", name),
        deficit.deficit_id,
        f"Bounded improvement may reduce {name.replace('_', ' ')}.",
        "improve targeted behavior without changing authority",
        0.78 if validation_passed else 0.52,
        (risk("scope_creep", "medium", "operator review and rollback"),),
        "validated" if validation_passed else "unresolved",
    )
    consultation = ConsultationDecision(
        stable_id("consultation", name, consultation_needed),
        hyp.hypothesis_id,
        consultation_needed,
        "rc6_disabled_gateway" if consultation_needed else "local_only",
        "consult only when local evidence is insufficient" if consultation_needed else "local evidence sufficient",
    )
    proposal = ImplementationProposal(
        stable_id("proposal", name),
        hyp.hypothesis_id,
        f"Prepare bounded proposal for {name.replace('_', ' ')}.",
        "single_subsystem_shadow_only",
        ("focused_test", "fast_validation"),
        ("reject_proposal", "restore_previous_behavior"),
    )
    validation = ValidationResult(
        stable_id("validation", name, validation_passed, regressions),
        proposal.proposal_id,
        validation_passed,
        {"target_metric": 0.9 if validation_passed else 0.45, "safety": 1.0},
        regressions if regressions else (() if validation_passed else ("validation_failed",)),
        ev,
    )
    comparison = compare_behavior(
        proposal,
        old_behavior=f"{name} failed or required manual interpretation.",
        new_behavior=f"{name} is handled by a bounded campaign artifact." if validation_passed else f"{name} remains unresolved.",
        benefits=("more inspectable development evidence",) if validation_passed else (),
        regressions=regressions,
        operator_workload_delta=workload_delta,
    )
    disposition = OperatorDisposition(
        stable_id("disposition", name, decision),
        proposal.proposal_id,
        decision,
        f"operator decision is {decision}",
        "retain_shadow_evidence" if decision == "accepted" else "revise_or_stop",
    )
    return DevelopmentCycle(stable_id("cycle", name, decision, validation_passed), deficit, hyp, consultation, proposal, validation, comparison, disposition)


def compare_behavior(
    proposal: ImplementationProposal,
    *,
    old_behavior: str,
    new_behavior: str,
    benefits: tuple[str, ...],
    regressions: tuple[str, ...],
    operator_workload_delta: float,
) -> ComparativeOutcome:
    if regressions:
        recommendation = "REJECT_OR_REVISE"
        confidence = 0.55
    elif benefits and operator_workload_delta <= 0.25:
        recommendation = "RETAIN_AFTER_OPERATOR_REVIEW"
        confidence = 0.82
    elif benefits:
        recommendation = "DEFER_FOR_WORKLOAD_REVIEW"
        confidence = 0.68
    else:
        recommendation = "MORE_EVIDENCE_REQUIRED"
        confidence = 0.5
    return ComparativeOutcome(
        stable_id("comparison", proposal.proposal_id, old_behavior, new_behavior, benefits, regressions, operator_workload_delta),
        proposal.proposal_id,
        old_behavior,
        new_behavior,
        benefits,
        regressions,
        operator_workload_delta,
        recommendation,
        confidence,
    )


def build_history(cycles: tuple[DevelopmentCycle, ...]) -> tuple[DevelopmentHistoryRecord, ...]:
    return tuple(
        DevelopmentHistoryRecord(
            stable_id("history", cycle.cycle_id),
            cycle.deficit.description,
            cycle.proposal.summary,
            cycle.disposition.decision,
            tuple(ev.summary for ev in cycle.validation.evidence),
            cycle.comparison.recommendation,
            "resolved" if cycle.validation.passed and cycle.disposition.decision == "accepted" else "unresolved",
        )
        for cycle in cycles
    )


def calculate_campaign_health(cycles: tuple[DevelopmentCycle, ...]) -> CampaignHealth:
    open_deficits = sum(1 for cycle in cycles if cycle.deficit.status == "open")
    resolved = sum(1 for cycle in cycles if cycle.deficit.status == "resolved")
    repeated_failures = sum(1 for cycle in cycles if cycle.deficit.recurrence >= 3 and not cycle.validation.passed)
    repeated_regressions = sum(1 for cycle in cycles if cycle.comparison.regressions)
    evidence_scores = [ev.quality for cycle in cycles for ev in cycle.validation.evidence]
    evidence_quality = statistics.mean(evidence_scores) if evidence_scores else 0.0
    workload = statistics.mean([abs(cycle.comparison.operator_workload_delta) for cycle in cycles]) if cycles else 0.0
    velocity = resolved / max(1, len(cycles))
    confidence = max(0.0, min(1.0, (evidence_quality * 0.4) + (velocity * 0.35) + ((1.0 - workload) * 0.25) - (repeated_regressions * 0.1)))
    stop_reasons = []
    if repeated_failures:
        stop_reasons.append("repeated_failures_require_operator_review")
    if repeated_regressions:
        stop_reasons.append("regressions_require_revision")
    if workload > 0.5:
        stop_reasons.append("operator_workload_high")
    return CampaignHealth(
        stable_id("health", len(cycles), open_deficits, resolved, repeated_failures, repeated_regressions),
        open_deficits,
        resolved,
        repeated_failures,
        repeated_regressions,
        round(velocity, 4),
        round(evidence_quality, 4),
        round(workload, 4),
        round(confidence, 4),
        bool(stop_reasons),
        tuple(stop_reasons),
    )


def build_campaign(title: str, cycles: tuple[DevelopmentCycle, ...]) -> DevelopmentCampaign:
    campaign_id = stable_id("campaign", title, tuple(c.cycle_id for c in cycles))
    health = calculate_campaign_health(cycles)
    checkpoint = CampaignCheckpoint(
        stable_id("checkpoint", campaign_id, "shadow-review"),
        campaign_id,
        "shadow_review",
        health.open_deficits,
        health.resolved_deficits,
        ";".join(health.stop_reasons) if health.stop_reasons else "none",
        health.evidence_quality,
    )
    priority = CampaignPriority(
        stable_id("priority", campaign_id, health.confidence),
        campaign_id,
        "operator_review" if health.stop_required else "normal_shadow_review",
        "operator owns reprioritization; RC7 only reports campaign state",
    )
    recommendation = "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS" if not health.stop_required else "REQUIRES_OPERATOR_REVIEW_BEFORE_CONTINUING"
    summary = CampaignSummary(
        stable_id("summary", campaign_id, recommendation),
        campaign_id,
        "shadow_only",
        recommendation,
        ("campaign state is inspectable", "comparative evidence is explicit", "operator authority preserved"),
        tuple(health.stop_reasons) if health.stop_reasons else ("real operator evidence still required before activation",),
        ("no autonomous execution", "no persistence changes", "no scheduling", "fixtures are not real operator evidence"),
    )
    confidence = CampaignConfidence(stable_id("confidence", campaign_id, health.confidence), health.confidence, ("evidence_quality", "resolution_velocity", "operator_workload"))
    return DevelopmentCampaign(campaign_id, title, "organize governed development without autonomous action", cycles, (checkpoint,), priority, health, summary, confidence)


def benchmark_fixtures() -> dict[str, DevelopmentCampaign]:
    return {
        "single_improvement": build_campaign("single improvement", (build_cycle("single_improvement"),)),
        "multiple_improvements": build_campaign("multiple improvements", (build_cycle("routing_fix"), build_cycle("summary_fix"))),
        "regression": build_campaign("regression", (build_cycle("regression_case", validation_passed=False, regressions=("conversation_regression",), decision="rejected"),)),
        "repeated_failure": build_campaign("repeated failure", (build_cycle("repeated_failure", recurrence=4, validation_passed=False, decision="deferred"),)),
        "deferred_hypothesis": build_campaign("deferred hypothesis", (build_cycle("deferred_hypothesis", validation_passed=False, decision="deferred"),)),
        "rejected_proposal": build_campaign("rejected proposal", (build_cycle("rejected_proposal", decision="rejected"),)),
        "successful_campaign": build_campaign("successful campaign", (build_cycle("first_success"), build_cycle("second_success"))),
        "abandoned_campaign": build_campaign("abandoned campaign", (build_cycle("abandoned_due_to_workload", validation_passed=False, decision="abandoned", workload_delta=0.8),)),
        "mixed_campaign": build_campaign("mixed campaign", (build_cycle("accepted_part"), build_cycle("rejected_part", decision="rejected", regressions=("scope_creep",), validation_passed=False))),
        "interrupted_campaign": build_campaign("interrupted campaign", (build_cycle("interruption_recorded", validation_passed=False, decision="deferred"),)),
        "resume_later": build_campaign("resume later", (build_cycle("resume_context_preserved"),)),
        "campaign_completion": build_campaign("campaign completion", (build_cycle("completion_evidence"),)),
        "campaign_cancellation": build_campaign("campaign cancellation", (build_cycle("cancellation", validation_passed=False, decision="abandoned"),)),
    }


def developmental_corpus() -> tuple[CampaignCorpusItem, ...]:
    records = (
        ("successful_upgrade", "UI routing failed", "add broad special case", "add bounded pre-router and regression", "focused test passed", "accepted", "retained"),
        ("failed_upgrade", "summary omitted packet blocks", "claim pilot passed", "fix accounting before claiming readiness", "operator transcript showed mismatch", "revised", "improved"),
        ("false_hypothesis", "provider gate failed", "add more concepts", "inspect routing and gateway first", "failure was not knowledge-related", "rejected", "avoided scope creep"),
        ("useful_consultation", "manual advice suggested tests", "apply immediately", "validate as advisory then prepare review", "advice contained useful test idea", "accepted_after_review", "bounded"),
        ("bad_consultation", "external advice bypassed authorization", "apply direct patch", "reject advice and keep governed handoff", "unsafe instruction present", "rejected", "blocked"),
        ("rollback", "repair failed validation", "retry indefinitely", "stop and preserve rollback evidence", "validation failure recorded", "stopped", "recovered"),
        ("scope_reduction", "proposal too broad", "refactor entire runtime", "narrow to one route calibration", "operator workload lower", "revised", "bounded"),
        ("operator_disagreement", "operator rejected freeze claim", "freeze anyway", "record partial evidence only", "insufficient rollback evidence", "rejected", "truthful"),
        ("reprioritization", "new pilot issue appeared", "continue old benchmark only", "rearbitrate campaign priority", "operator changed priority", "deferred", "queued"),
    )
    return tuple(CampaignCorpusItem(stable_id("corpus", *record), *record) for record in records)


def adversarial_campaign_cases() -> tuple[dict[str, Any], ...]:
    cases = []
    scenarios = (
        ("repeated_failures", build_cycle("repeated_failures", recurrence=5, validation_passed=False, decision="deferred"), "stop_required"),
        ("contradictory_evidence", build_cycle("contradictory_evidence", validation_passed=False, regressions=("conflicting_metrics",), decision="rejected"), "stop_required"),
        ("bad_consultation", build_cycle("bad_consultation", validation_passed=False, regressions=("unsafe_advice",), decision="rejected", consultation_needed=True), "stop_required"),
        ("scope_creep", build_cycle("scope_creep", validation_passed=False, regressions=("scope_creep",), decision="rejected"), "stop_required"),
        ("missing_evidence", build_cycle("missing_evidence", validation_passed=False, decision="deferred"), "more_evidence"),
        ("campaign_starvation", build_cycle("campaign_starvation", validation_passed=False, decision="deferred", workload_delta=0.9), "stop_required"),
    )
    for name, cycle, expectation in scenarios:
        campaign = build_campaign(name, (cycle,))
        cases.append({
            "case": name,
            "expectation": expectation,
            "stop_required": campaign.health.stop_required,
            "stop_reasons": campaign.health.stop_reasons,
            "passed": campaign.health.stop_required if expectation == "stop_required" else campaign.health.open_deficits > 0,
        })
    return tuple(cases)


def build_operator_dashboard_snapshot(campaign: DevelopmentCampaign | None = None) -> dict[str, Any]:
    if campaign is None:
        campaign = benchmark_fixtures()["successful_campaign"]
    latest = campaign.cycles[-1] if campaign.cycles else None
    return {
        "current_campaign": campaign.title,
        "current_hypothesis": latest.hypothesis.summary if latest else "none",
        "open_deficits": campaign.health.open_deficits,
        "consultation_status": latest.consultation.channel if latest else "none",
        "validation_status": "passed" if latest and latest.validation.passed else "not_passed",
        "comparison": latest.comparison.recommendation if latest else "none",
        "outstanding_evidence": tuple(c.deficit.description for c in campaign.cycles if c.deficit.status == "open"),
        "campaign_health": asdict(campaign.health),
        "hidden_authority_exposed": False,
        "safety": safety_metadata(),
    }


def render_operator_dashboard(snapshot: Mapping[str, Any]) -> str:
    health = snapshot.get("campaign_health", {})
    return "\n".join([
        "RC7 Development Dashboard",
        f"Current campaign: {snapshot.get('current_campaign')}",
        f"Current hypothesis: {snapshot.get('current_hypothesis')}",
        f"Open deficits: {snapshot.get('open_deficits')}",
        f"Consultation status: {snapshot.get('consultation_status')}",
        f"Validation status: {snapshot.get('validation_status')}",
        f"Comparison: {snapshot.get('comparison')}",
        f"Outstanding evidence: {', '.join(snapshot.get('outstanding_evidence') or ()) or 'none'}",
        f"Campaign confidence: {health.get('confidence')}",
        f"Stop required: {health.get('stop_required')}",
        "Authority: observational dashboard only; no execution, provider call, schedule, approval, or persistence.",
    ])


def development_loop_benchmark() -> dict[str, Any]:
    fixtures = benchmark_fixtures()
    corpus = developmental_corpus()
    adversarial = adversarial_campaign_cases()
    successful = fixtures["successful_campaign"]
    mixed = fixtures["mixed_campaign"]
    checks = {
        "fixture_count": len(fixtures) >= 12,
        "successful_campaign_ready": successful.summary.recommendation == "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS",
        "mixed_campaign_stops": mixed.health.stop_required is True,
        "history_records": len(build_history(successful.cycles)) == len(successful.cycles),
        "corpus_coverage": len(corpus) >= 9,
        "adversarial_cases_pass": all(case["passed"] for case in adversarial),
        "safety_no_execution": not any(safety_metadata().values()),
    }
    return {
        "report": "RC7_DEVELOPMENT_LOOP_FOUNDATION",
        "passed": all(checks.values()),
        "score": round(sum(checks.values()) / len(checks), 4),
        "checks": checks,
        "fixture_names": tuple(fixtures.keys()),
        "corpus_count": len(corpus),
        "adversarial_cases": adversarial,
        "sample_campaign": asdict(successful),
        "dashboard": build_operator_dashboard_snapshot(successful),
        "recommendation": "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS" if all(checks.values()) else "CONTINUE_RC7_CALIBRATION",
        "safety": safety_metadata(),
    }


def campaign_readiness_report() -> dict[str, Any]:
    fixtures = benchmark_fixtures()
    health_scores = [campaign.health.confidence for campaign in fixtures.values()]
    stop_count = sum(1 for campaign in fixtures.values() if campaign.health.stop_required)
    checks = {
        "campaigns_model_success_failure_and_mixed": {"successful_campaign", "repeated_failure", "mixed_campaign"}.issubset(fixtures.keys()),
        "stop_conditions_present": stop_count >= 4,
        "average_confidence_bounded": 0.0 <= statistics.mean(health_scores) <= 1.0,
        "operator_owns_priority": all(campaign.priority.operator_owned for campaign in fixtures.values()),
        "no_persistence_or_execution": not any(safety_metadata().values()),
    }
    return {
        "report": "RC7_CAMPAIGN_READINESS",
        "passed": all(checks.values()),
        "checks": checks,
        "campaign_count": len(fixtures),
        "stop_required_count": stop_count,
        "average_confidence": round(statistics.mean(health_scores), 4),
        "recommendation": "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS" if all(checks.values()) else "CONTINUE_RC7_CAMPAIGN_MODELING",
        "known_limitations": (
            "fixtures are deterministic and not real operator evidence",
            "campaigns do not execute",
            "history is conversation-scoped unless explicitly exported elsewhere",
        ),
        "safety": safety_metadata(),
    }


def operator_dashboard_report() -> dict[str, Any]:
    snapshot = build_operator_dashboard_snapshot()
    rendered = render_operator_dashboard(snapshot)
    checks = {
        "current_campaign_visible": "Current campaign:" in rendered,
        "hypothesis_visible": "Current hypothesis:" in rendered,
        "health_visible": "Campaign confidence:" in rendered,
        "authority_boundary_visible": "no execution" in rendered.lower(),
        "hidden_authority_not_exposed": snapshot["hidden_authority_exposed"] is False,
    }
    return {
        "report": "RC7_OPERATOR_DASHBOARD",
        "passed": all(checks.values()),
        "checks": checks,
        "snapshot": snapshot,
        "rendered": rendered,
        "recommendation": "DASHBOARD_READY_FOR_DEVELOPER_OVERLAY" if all(checks.values()) else "CONTINUE_DASHBOARD_CALIBRATION",
        "safety": safety_metadata(),
    }


def write_reports() -> dict[str, Any]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reports = {
        "RC7_DEVELOPMENT_LOOP_FOUNDATION": development_loop_benchmark(),
        "RC7_CAMPAIGN_READINESS": campaign_readiness_report(),
        "RC7_OPERATOR_DASHBOARD": operator_dashboard_report(),
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
        "",
        "## Strengths",
        "- Development is represented as governed campaigns.",
        "- Comparative evaluation is explicit.",
        "- Operator decisions remain authoritative.",
        "",
        "## Weaknesses / Limitations",
        "- Fixtures are not real operator evidence.",
        "- RC7 does not execute campaigns or proposals.",
        "- No scheduling or persistence changes are enabled.",
        "",
        "## Safety",
    ]
    for key, value in safety_metadata().items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Payload", "```json", json.dumps(payload, indent=2, sort_keys=True)[:14000], "```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_reports()
    print(json.dumps({key: value.get("recommendation") for key, value in result.items()}, indent=2, sort_keys=True))
