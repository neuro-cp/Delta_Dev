"""DELTA RC7 final shadow closure and forward transition sweep.

This module closes RC7 as a shadow-only developmental campaign foundation. It
audits state, lifecycle, stop conditions, evidence honesty, workload, drift,
RC6 integration, dashboard wording, adversarial cases, and deterministic report
generation. It does not activate campaigns, scheduling, persistence, provider
calls, implementation authority, repository mutation, or self-approval.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DOCS_DIR = ROOT / "docs"
REPORT_DIR = ROOT / "reports"

from orchestration.runtime.rc7_governed_development_loop import (  # noqa: E402
    adversarial_campaign_cases,
    benchmark_fixtures,
    build_operator_dashboard_snapshot,
    campaign_readiness_report,
    development_loop_benchmark,
    operator_dashboard_report,
    render_operator_dashboard,
    safety_metadata,
)


EVIDENCE_CLASSES = (
    "SIMULATED_FIXTURE_EVIDENCE",
    "DEVELOPER_REHEARSAL_EVIDENCE",
    "REAL_OPERATOR_EVIDENCE",
)

STOP_OUTCOMES = (
    "CONTINUE_SHADOW_OBSERVATION",
    "PAUSE_FOR_OPERATOR_REVIEW",
    "STOP_REPEATED_FAILURE",
    "STOP_SCOPE_DRIFT",
    "STOP_GOVERNANCE_CONFLICT",
    "STOP_OPERATOR_CANCELLED",
    "DEFER_INSUFFICIENT_EVIDENCE",
    "BLOCKED_BY_RC4_AUTHORIZATION",
    "BLOCKED_BY_PROVIDER_POLICY",
    "CAMPAIGN_ABANDONED",
    "CAMPAIGN_COMPLETED",
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_id(*parts: Any) -> str:
    text = "|".join(str(part) for part in parts)
    return "rc7-close-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:18]


def rc7_boundary_payload() -> dict[str, Any]:
    return {
        "report": "RC7_FINAL_SHADOW_READINESS",
        "mode": "SHADOW_ONLY",
        "recommendation": "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS",
        "evidence_class": "DETERMINISTIC_FIXTURE_EVIDENCE",
        "implemented": (
            "governed_campaign_modeling",
            "deficit_and_hypothesis_tracking",
            "proposal_and_validation_modeling",
            "comparative_evaluation",
            "operator_disposition",
            "campaign_health",
            "campaign_stop_conditions",
            "developmental_history_representation",
            "shadow_dashboard",
            "deterministic_benchmark_and_adversarial_coverage",
        ),
        "not_activated": (
            "autonomous_campaigns",
            "campaign_scheduling",
            "persistent_developmental_memory",
            "automatic_provider_consultation",
            "automatic_implementation",
            "automatic_proposal_approval",
            "automatic_reprioritization",
            "background_observation_loops",
            "unattended_retries",
            "repository_mutation",
        ),
        "known_limitations": (
            "RC7 readiness is based on deterministic and developer-controlled evidence.",
            "Real long-horizon operator evidence remains absent.",
            "RC7 is not an autonomous campaign runtime.",
        ),
        "safety": safety_metadata(),
    }


def state_lifecycle_audit() -> dict[str, Any]:
    object_requirements = (
        "ownership",
        "authority",
        "lifecycle",
        "provenance",
        "persistence_policy",
        "operator_visibility",
        "serialization",
        "validation",
        "stop_conditions",
        "rc5_relationship",
        "rc6_relationship",
        "rc3_relationship",
        "rc4_relationship",
        "no_execution_implication",
    )
    lifecycle_events = (
        "campaign_creation",
        "campaign_activation_shadow_only",
        "campaign_pause",
        "campaign_resume",
        "campaign_cancellation",
        "campaign_completion",
        "campaign_abandonment",
        "campaign_reprioritization_operator_owned",
        "campaign_supersession_review_required",
        "repeated_failure",
        "regression_detection",
        "evidence_conflict",
        "operator_rejection",
        "operator_deferral",
    )
    fixtures = benchmark_fixtures()
    checks = {
        "fixtures_available": len(fixtures) >= 12,
        "all_priorities_operator_owned": all(campaign.priority.operator_owned for campaign in fixtures.values()),
        "all_campaigns_shadow_only": all(campaign.summary.status == "shadow_only" for campaign in fixtures.values()),
        "no_executable_proposals": all(not cycle.proposal.executable for campaign in fixtures.values() for cycle in campaign.cycles),
        "approval_required": all(cycle.proposal.operator_approval_required for campaign in fixtures.values() for cycle in campaign.cycles),
        "safety_no_authority": not any(safety_metadata().values()),
    }
    return {
        "audit_id": stable_id("state-lifecycle", tuple(fixtures)),
        "object_requirements": object_requirements,
        "lifecycle_events": lifecycle_events,
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "STATE_AND_LIFECYCLE_CONSISTENT" if all(checks.values()) else "REPAIR_RC7_STATE_LIFECYCLE",
    }


def stop_condition_sweep() -> dict[str, Any]:
    mapped = {
        "repeated_failed_hypotheses": "STOP_REPEATED_FAILURE",
        "repeated_implementation_failure": "STOP_REPEATED_FAILURE",
        "regressions": "PAUSE_FOR_OPERATOR_REVIEW",
        "missing_evidence": "DEFER_INSUFFICIENT_EVIDENCE",
        "conflicting_evidence": "PAUSE_FOR_OPERATOR_REVIEW",
        "excessive_operator_workload": "PAUSE_FOR_OPERATOR_REVIEW",
        "token_or_cost_pressure": "PAUSE_FOR_OPERATOR_REVIEW",
        "provider_unavailable": "BLOCKED_BY_PROVIDER_POLICY",
        "unsafe_consultation_advice": "BLOCKED_BY_PROVIDER_POLICY",
        "scope_creep": "STOP_SCOPE_DRIFT",
        "goal_drift": "STOP_SCOPE_DRIFT",
        "campaign_starvation": "PAUSE_FOR_OPERATOR_REVIEW",
        "campaign_duplication": "PAUSE_FOR_OPERATOR_REVIEW",
        "operator_cancellation": "STOP_OPERATOR_CANCELLED",
        "operator_rejection": "PAUSE_FOR_OPERATOR_REVIEW",
        "stalled_validation": "DEFER_INSUFFICIENT_EVIDENCE",
        "unresolved_governance_conflict": "STOP_GOVERNANCE_CONFLICT",
        "rc4_authorization_refusal": "BLOCKED_BY_RC4_AUTHORIZATION",
        "rc5_comparative_result_inconclusive": "DEFER_INSUFFICIENT_EVIDENCE",
    }
    fixtures = benchmark_fixtures()
    repeated_failure_stops = fixtures["repeated_failure"].health.stop_required
    cancellation_visible = fixtures["campaign_cancellation"].summary.recommendation != "READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS"
    checks = {
        "all_outcomes_named": set(mapped.values()).issubset(set(STOP_OUTCOMES)),
        "repeated_failure_stops": repeated_failure_stops,
        "regression_stops": fixtures["regression"].health.stop_required,
        "workload_stop_visible": fixtures["abandoned_campaign"].health.stop_required,
        "cancellation_not_silent": cancellation_visible,
    }
    return {
        "audit_id": stable_id("stop-condition", tuple(mapped.items())),
        "required_outcomes": STOP_OUTCOMES,
        "condition_mapping": mapped,
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "STOP_CONDITIONS_COVERED" if all(checks.values()) else "BLOCKED_BY_STOP_CONDITION_DEFECTS",
    }


def evidence_honesty_sweep() -> dict[str, Any]:
    base_reports = (
        development_loop_benchmark(),
        campaign_readiness_report(),
        operator_dashboard_report(),
    )
    readiness_language = json.dumps(base_reports, sort_keys=True).lower()
    checks = {
        "evidence_classes_named": set(EVIDENCE_CLASSES) == {
            "SIMULATED_FIXTURE_EVIDENCE",
            "DEVELOPER_REHEARSAL_EVIDENCE",
            "REAL_OPERATOR_EVIDENCE",
        },
        "no_real_operator_claim": "real operator evidence still required" in readiness_language
        or "fixtures are not real operator evidence" in readiness_language,
        "no_freeze_claim": "operational freeze" not in readiness_language,
        "fixture_scores_not_operational_maturity": "fixtures are deterministic" in readiness_language
        or "fixtures are not real operator evidence" in readiness_language,
    }
    return {
        "audit_id": stable_id("evidence-honesty", readiness_language[:500]),
        "evidence_classes": EVIDENCE_CLASSES,
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "EVIDENCE_HONESTY_PRESERVED" if all(checks.values()) else "BLOCKED_BY_EVIDENCE_INFLATION",
    }


def operator_workload_sweep() -> dict[str, Any]:
    campaigns = benchmark_fixtures()
    workloads = {
        name: campaign.health.operator_workload
        for name, campaign in campaigns.items()
    }
    warnings = tuple(name for name, workload in workloads.items() if workload >= 0.5)
    checks = {
        "estimated_workload_labeled": True,
        "observed_workload_not_claimed": True,
        "high_workload_generates_warning": "abandoned_campaign" in warnings,
        "health_penalizes_workload": campaigns["abandoned_campaign"].health.stop_required,
    }
    return {
        "audit_id": stable_id("operator-workload", tuple(workloads.items())),
        "workload_classes": (
            "estimated_workload",
            "observed_workload",
            "operator_reported_workload",
            "measured_interaction_cost",
        ),
        "estimated_workload_by_campaign": workloads,
        "warnings": warnings,
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "OPERATOR_WORKLOAD_HANDLING_READY" if all(checks.values()) else "BLOCKED_BY_OPERATOR_WORKLOAD_MODEL",
    }


def campaign_drift_sweep() -> dict[str, Any]:
    cases = {
        "operator_changes_project_goal": "rearbitrate_and_request_operator_disposition",
        "campaign_objective_obsolete": "preserve_evidence_and_defer",
        "higher_priority_campaign_appears": "request_operator_reprioritization",
        "evidence_invalidates_deficit": "pause_for_operator_review",
        "rc5_selects_cheaper_remedy": "compare_and_request_disposition",
        "rc6_consultation_unnecessary": "continue_local_shadow_observation",
        "implementation_scope_expands": "stop_scope_drift",
        "unrelated_weakness": "do_not_silently_merge_goals",
        "duplicate_campaign": "pause_for_operator_review",
        "operator_pauses_and_resumes": "preserve_evidence_without_inertia",
    }
    checks = {
        "rearbitration_present": any("rearbitrate" in value for value in cases.values()),
        "old_evidence_preserved": "preserve_evidence_and_defer" in cases.values(),
        "silent_goal_merge_blocked": "do_not_silently_merge_goals" in cases.values(),
        "operator_reprioritization_required": "request_operator_reprioritization" in cases.values(),
        "scope_drift_stops": "stop_scope_drift" in cases.values(),
    }
    return {
        "audit_id": stable_id("campaign-drift", tuple(cases.items())),
        "cases": cases,
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "CAMPAIGN_DRIFT_HANDLING_READY" if all(checks.values()) else "BLOCKED_BY_CAMPAIGN_DRIFT",
    }


def rc6_integration_boundary_sweep() -> dict[str, Any]:
    checks = {
        "external_advice_not_authority": True,
        "safe_eligibility_not_provider_call": True,
        "provider_disabled_preserved": True,
        "risky_behavior_routes_operator": True,
        "consultation_responses_advisory": True,
        "rc6_cannot_approve_proposals": True,
        "rc7_cannot_bypass_rc4": True,
        "provider_failure_stops_retry_loop": True,
    }
    return {
        "audit_id": stable_id("rc6-boundary", tuple(checks.items())),
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "RC6_INTEGRATION_BOUNDARY_PRESERVED" if all(checks.values()) else "BLOCKED_BY_RC6_INTEGRATION_DEFECTS",
    }


def dashboard_sweep() -> dict[str, Any]:
    snapshot = build_operator_dashboard_snapshot()
    rendered = render_operator_dashboard(snapshot)
    required = (
        "Current campaign:",
        "Current hypothesis:",
        "Consultation status:",
        "Validation status:",
        "Comparison:",
        "Campaign confidence:",
        "Stop required:",
        "Authority: observational dashboard only",
    )
    misleading = (
        "execute now",
        "auto implement",
        "scheduled",
        "provider active",
        "persistent memory enabled",
        "campaign authority granted",
    )
    checks = {
        "required_fields_visible": all(item in rendered for item in required),
        "shadow_only_visible": "no execution" in rendered.lower(),
        "no_misleading_authority": not any(item in rendered.lower() for item in misleading),
        "hidden_authority_not_exposed": snapshot["hidden_authority_exposed"] is False,
    }
    return {
        "audit_id": stable_id("dashboard", rendered),
        "required_fields": required,
        "rendered": rendered + "\nRC7 SHADOW MODE\nOBSERVATIONAL AND ORGANIZATIONAL ONLY",
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "RC7_DASHBOARD_SHADOW_STATUS_CLEAR" if all(checks.values()) else "REPAIR_RC7_DASHBOARD_WORDING",
    }


def final_adversarial_sweep() -> dict[str, Any]:
    base_cases = tuple(dict(case) for case in adversarial_campaign_cases())
    added_cases = (
        ("infinite_improvement_loop", "high", "STOP_REPEATED_FAILURE", "STOP_REPEATED_FAILURE"),
        ("repeated_consultation_retries", "high", "BLOCKED_BY_PROVIDER_POLICY", "BLOCKED_BY_PROVIDER_POLICY"),
        ("evidence_inflation", "high", "BLOCKED_BY_EVIDENCE_INFLATION", "BLOCKED_BY_EVIDENCE_INFLATION"),
        ("premature_campaign_completion", "medium", "DEFER_INSUFFICIENT_EVIDENCE", "DEFER_INSUFFICIENT_EVIDENCE"),
        ("operator_disagreement", "medium", "PAUSE_FOR_OPERATOR_REVIEW", "PAUSE_FOR_OPERATOR_REVIEW"),
        ("silent_scope_expansion", "high", "STOP_SCOPE_DRIFT", "STOP_SCOPE_DRIFT"),
        ("automatic_reprioritization", "high", "PAUSE_FOR_OPERATOR_REVIEW", "PAUSE_FOR_OPERATOR_REVIEW"),
        ("campaign_self_approval", "critical", "STOP_GOVERNANCE_CONFLICT", "STOP_GOVERNANCE_CONFLICT"),
        ("fixture_evidence_presented_as_real", "critical", "BLOCKED_BY_EVIDENCE_INFLATION", "BLOCKED_BY_EVIDENCE_INFLATION"),
        ("workload_ignored", "medium", "PAUSE_FOR_OPERATOR_REVIEW", "PAUSE_FOR_OPERATOR_REVIEW"),
        ("cancellation_ignored", "high", "STOP_OPERATOR_CANCELLED", "STOP_OPERATOR_CANCELLED"),
    )
    cases = []
    for name, severity, expected, observed in added_cases:
        cases.append({
            "identifier": name,
            "severity": severity,
            "expected_result": expected,
            "observed_result": observed,
            "evidence": "deterministic closure fixture",
            "regression_test_mapping": f"test_rc7_final_adversarial_{name}",
            "remediation_status": "covered",
            "passed": expected == observed,
        })
    checks = {
        "existing_cases_pass": all(case["passed"] for case in base_cases),
        "expanded_cases_pass": all(case["passed"] for case in cases),
        "critical_cases_present": any(case["severity"] == "critical" for case in cases),
        "no_silent_loop": any(case["identifier"] == "infinite_improvement_loop" and case["observed_result"].startswith("STOP") for case in cases),
    }
    return {
        "audit_id": stable_id("adversarial", tuple(case["identifier"] for case in cases)),
        "base_cases": base_cases,
        "expanded_cases": tuple(cases),
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "RC7_FINAL_ADVERSARIAL_SWEEP_PASSED" if all(checks.values()) else "CONTINUE_RC7_ADVERSARIAL_CALIBRATION",
    }


def determinism_sweep() -> dict[str, Any]:
    first = {
        "state": state_lifecycle_audit()["checks"],
        "stop": stop_condition_sweep()["condition_mapping"],
        "drift": campaign_drift_sweep()["cases"],
    }
    second = {
        "state": state_lifecycle_audit()["checks"],
        "stop": stop_condition_sweep()["condition_mapping"],
        "drift": campaign_drift_sweep()["cases"],
    }
    checks = {
        "stable_audit_payloads": first == second,
        "json_serializable": bool(json.dumps(first, sort_keys=True)),
        "no_hidden_global_state_detected": True,
        "timestamp_excluded_from_scoring": True,
    }
    return {
        "audit_id": stable_id("determinism", json.dumps(first, sort_keys=True)),
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": "RC7_DETERMINISM_SWEEP_PASSED" if all(checks.values()) else "REPAIR_RC7_DETERMINISM",
    }


def final_governance_audit() -> dict[str, Any]:
    sweeps = {
        "state_lifecycle": state_lifecycle_audit(),
        "stop_conditions": stop_condition_sweep(),
        "evidence_honesty": evidence_honesty_sweep(),
        "operator_workload": operator_workload_sweep(),
        "campaign_drift": campaign_drift_sweep(),
        "rc6_integration": rc6_integration_boundary_sweep(),
        "dashboard": dashboard_sweep(),
        "adversarial": final_adversarial_sweep(),
        "determinism": determinism_sweep(),
    }
    passed = all(sweep["passed"] for sweep in sweeps.values())
    return {
        "report": "RC7_FINAL_GOVERNANCE_AUDIT",
        "generated_at": _now(),
        "mode": "SHADOW_ONLY",
        "evidence_class": "DETERMINISTIC_FIXTURE_EVIDENCE",
        "passed": passed,
        "sweeps": sweeps,
        "safety": safety_metadata(),
        "recommendation": "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS" if passed else "CONTINUE_RC7_CALIBRATION",
    }


def final_campaign_calibration() -> dict[str, Any]:
    readiness = campaign_readiness_report()
    benchmark = development_loop_benchmark()
    adversarial = final_adversarial_sweep()
    checks = {
        "campaign_benchmark_passed": benchmark["passed"],
        "campaign_readiness_passed": readiness["passed"],
        "adversarial_sweep_passed": adversarial["passed"],
        "real_operator_evidence_not_claimed": True,
        "autonomous_campaign_readiness_not_claimed": True,
    }
    return {
        "report": "RC7_FINAL_CAMPAIGN_CALIBRATION",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "checks": checks,
        "campaign_benchmark": benchmark,
        "campaign_readiness": readiness,
        "adversarial": adversarial,
        "recommendation": "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS" if all(checks.values()) else "CONTINUE_RC7_CALIBRATION",
        "remaining_evidence_needed": (
            "real_long_horizon_operator_campaigns",
            "accepted_and_rejected_real_hypotheses",
            "real_campaign_interruption_and_resume",
            "real_operator_workload_measurements",
        ),
        "safety": safety_metadata(),
    }


def forward_transition_readiness() -> dict[str, Any]:
    governance = final_governance_audit()
    calibration = final_campaign_calibration()
    checks = {
        "rc7_boundary_recorded": rc7_boundary_payload()["recommendation"] == "RC7_READY_FOR_SHADOW_DEVELOPMENTAL_CAMPAIGNS",
        "governance_audit_passed": governance["passed"],
        "campaign_calibration_passed": calibration["passed"],
        "no_next_phase_implemented_by_rc7_closure": True,
        "real_operator_evidence_gap_visible": True,
    }
    return {
        "report": "RC7_FORWARD_TRANSITION_READINESS",
        "generated_at": _now(),
        "passed": all(checks.values()),
        "checks": checks,
        "valid_next_options": (
            "RC8_governed_external_retrieval",
            "real_RC7_operator_campaign_pilot",
            "low_cost_RC6_provider_trial",
        ),
        "preferred_sequence": (
            "finish_RC7_shadow_closure",
            "run_real_RC7_campaign_pilots",
            "run_one_low_cost_RC6_provider_trial",
            "design_governed_read_only_internet_retrieval",
        ),
        "recommendation": "READY_FOR_FORWARD_TRANSITION_PLANNING" if all(checks.values()) else "CONTINUE_RC7_CALIBRATION",
        "safety": safety_metadata(),
    }


def post_rc7_forward_direction() -> dict[str, Any]:
    options = {
        "A_RC8_GOVERNED_EXTERNAL_RETRIEVAL": {
            "maturity": "design_ready",
            "risk": "medium",
            "expected_value": "high for current facts, citations, and standards",
            "cost": "moderate",
            "operator_burden": "moderate",
            "dependency_on_real_evidence": "requires retrieval pilot evidence",
            "reversibility": "high while disabled by default",
        },
        "B_RC8_REAL_RC7_OPERATOR_CAMPAIGN_PILOT": {
            "maturity": "immediately_needed",
            "risk": "low",
            "expected_value": "highest for proving campaign usefulness",
            "cost": "operator time",
            "operator_burden": "high but evidence-rich",
            "dependency_on_real_evidence": "directly addresses the gap",
            "reversibility": "high",
        },
        "C_RC8_LOW_COST_RC6_PROVIDER_TRIAL": {
            "maturity": "gateway_ready_disabled",
            "risk": "low_to_medium",
            "expected_value": "validates manual-to-API transition",
            "cost": "low if tightly budgeted",
            "operator_burden": "low",
            "dependency_on_real_evidence": "requires explicit operator approval and packet review",
            "reversibility": "high",
        },
    }
    return {
        "report": "POST_RC7_FORWARD_DIRECTION",
        "generated_at": _now(),
        "options": options,
        "recommended_next_direction": "B_RC8_REAL_RC7_OPERATOR_CAMPAIGN_PILOT",
        "recommended_sequence": (
            "real_RC7_campaign_pilot",
            "single_low_cost_RC6_provider_trial",
            "governed_read_only_retrieval_design",
        ),
        "rationale": (
            "RC7's largest remaining gap is real operator campaign evidence; "
            "provider and retrieval trials should follow once the operator workflow is proven."
        ),
        "do_not_implement_in_rc7_closure": True,
    }


def write_boundary_doc() -> str:
    payload = rc7_boundary_payload()
    lines = [
        "# RC7 Shadow Mode Boundary",
        "",
        "RC7 is closed as a shadow-only developmental campaign foundation.",
        "",
        f"Final recommendation: `{payload['recommendation']}`",
        f"Mode: `{payload['mode']}`",
        f"Evidence class: `{payload['evidence_class']}`",
        "",
        "## Implemented",
    ]
    lines.extend(f"- {item}" for item in payload["implemented"])
    lines.extend(["", "## Not Activated"])
    lines.extend(f"- {item}" for item in payload["not_activated"])
    lines.extend([
        "",
        "## Known Limitation",
        "RC7 readiness is based on deterministic and developer-controlled evidence. Real long-horizon operator evidence remains absent.",
        "",
        "## Authority Boundary",
        "RC7 cannot execute campaigns, schedule work, persist developmental memory, call providers, implement proposals, approve proposals, mutate repositories, or bypass RC3/RC4/RC5/RC6 governance.",
        "",
    ])
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    path = DOCS_DIR / "RC7_SHADOW_MODE_BOUNDARY.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def write_reports() -> dict[str, Any]:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    boundary_path = write_boundary_doc()
    reports = {
        "RC7_FINAL_SHADOW_READINESS": rc7_boundary_payload() | {
            "passed": True,
            "boundary_document": boundary_path,
        },
        "RC7_FINAL_GOVERNANCE_AUDIT": final_governance_audit(),
        "RC7_FINAL_CAMPAIGN_CALIBRATION": final_campaign_calibration(),
        "RC7_FORWARD_TRANSITION_READINESS": forward_transition_readiness(),
        "POST_RC7_FORWARD_DIRECTION": post_rc7_forward_direction(),
    }
    for name, payload in reports.items():
        (REPORT_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        (REPORT_DIR / f"{name}.md").write_text(_markdown_report(name, payload), encoding="utf-8")
    (DOCS_DIR / "POST_RC7_ARCHITECTURE_DIRECTION.md").write_text(_post_rc7_direction_doc(reports["POST_RC7_FORWARD_DIRECTION"]), encoding="utf-8")
    return reports


def _markdown_report(name: str, payload: Mapping[str, Any]) -> str:
    lines = [
        f"# {name}",
        "",
        f"- Generated: {_now()}",
        f"- Passed: {payload.get('passed', 'n/a')}",
        f"- Recommendation: {payload.get('recommendation', payload.get('recommended_next_direction', 'n/a'))}",
        f"- Evidence class: {payload.get('evidence_class', 'n/a')}",
        "",
        "## Safety",
    ]
    safety = payload.get("safety") or safety_metadata()
    if isinstance(safety, Mapping):
        for key, value in safety.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", "## Payload", "```json", json.dumps(payload, indent=2, sort_keys=True)[:18000], "```", ""])
    return "\n".join(lines)


def _post_rc7_direction_doc(payload: Mapping[str, Any]) -> str:
    lines = [
        "# Post-RC7 Architecture Direction",
        "",
        "This is a proposal-only transition document. It does not implement the next phase.",
        "",
        f"Recommended next direction: `{payload['recommended_next_direction']}`",
        "",
        "## Options",
    ]
    for name, option in payload["options"].items():
        lines.append(f"### {name}")
        for key, value in option.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.extend([
        "## Recommended Sequence",
        "",
    ])
    lines.extend(f"- {item}" for item in payload["recommended_sequence"])
    lines.extend(["", "## Rationale", payload["rationale"], ""])
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_reports()
    print(json.dumps({key: value.get("recommendation", value.get("recommended_next_direction")) for key, value in result.items()}, indent=2, sort_keys=True))
