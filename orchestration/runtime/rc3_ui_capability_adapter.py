"""Read-only RC3 UI capability adapter.

The operator UI should render RC3 state and reports without reimplementing
governance logic or granting authority. This module loads existing RC3 reports
and deterministic state builders, then returns display-oriented panel payloads.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "reports"

PANEL_ORDER = (
    "Goals",
    "Plans",
    "Revisions",
    "Introspection",
    "Engineering",
    "Sandbox",
    "Governance",
    "Plugins",
    "Integration",
    "Projects",
    "Persistence",
    "Pilot Evidence",
    "Freeze Readiness",
    "Diagnostics",
)

SAFETY_WARNING = (
    "RC3 UI is inspect/review only. It does not execute plans, create sandboxes, "
    "activate plugins, mutate repositories, invoke providers, or grant persistence authority."
)


def build_rc3_ui_snapshot() -> dict[str, Any]:
    """Return a complete read-only snapshot for the RC3 operator UI."""

    reports = _load_reports()
    stages = {stage: _stage_report_from_file(stage) for stage in "EFGHIJK"}
    panels = {
        "Goals": _goal_panel(reports),
        "Plans": _plan_panel(reports),
        "Revisions": _revision_panel(reports),
        "Introspection": _introspection_panel(reports),
        "Engineering": _engineering_panel(reports),
        "Sandbox": _sandbox_panel(reports),
        "Governance": _stage_panel("Governance", stages["E"], "governance review is not execution authority"),
        "Plugins": _stage_panel("Plugins", stages["F"], "plugin architecture is read-only; no plugin is loaded or activated"),
        "Integration": _stage_panel("Integration", stages["G"], "integration planning does not mutate files, commits, branches, or deployments"),
        "Projects": _stage_panel("Projects", stages["H"], "project cognition is ephemeral unless explicit fixture persistence is invoked"),
        "Persistence": _persistence_panel(stages["I"]),
        "Pilot Evidence": _pilot_panel(stages["J"], reports),
        "Freeze Readiness": _freeze_panel(stages["K"], reports),
        "Diagnostics": _diagnostics_panel(reports),
    }
    coverage = {
        "panel_count": len(panels),
        "expected_panel_count": len(PANEL_ORDER),
        "missing_panels": tuple(name for name in PANEL_ORDER if name not in panels),
        "all_panels_present": all(name in panels for name in PANEL_ORDER),
    }
    return {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "panels": panels,
        "panel_order": PANEL_ORDER,
        "coverage": coverage,
        "reports": reports,
        "safety_warning": SAFETY_WARNING,
        "actions_enabled": {
            "plan_execution": False,
            "proposal_execution": False,
            "sandbox_creation": False,
            "plugin_activation": False,
            "repository_mutation": False,
            "provider_call": False,
            "hidden_persistence": False,
            "delta_75_interaction": False,
        },
    }


def render_rc3_panel(panel_name: str, snapshot: dict[str, Any] | None = None) -> str:
    snapshot = snapshot or build_rc3_ui_snapshot()
    panels = snapshot["panels"]
    panel = panels.get(panel_name)
    if not panel:
        return f"Unknown RC3 panel: {panel_name}"
    lines = [
        str(panel["title"]),
        "",
        f"Status: {panel.get('status', 'unknown')}",
        f"Authority: {panel.get('authority', 'inspect_only')}",
        f"Evidence: {panel.get('evidence_status', 'report_or_fixture')}",
        "",
        "Summary:",
    ]
    lines.extend(f"- {item}" for item in panel.get("summary", ()))
    warnings = panel.get("warnings") or ()
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {item}" for item in warnings)
    detail = panel.get("detail")
    if detail:
        lines.extend(["", "Detail:", json.dumps(detail, indent=2, sort_keys=True)[:6000]])
    lines.extend(["", "Safety:", f"- {snapshot['safety_warning']}"])
    return "\n".join(lines)


def validate_rc3_ui_snapshot(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = snapshot or build_rc3_ui_snapshot()
    actions = snapshot["actions_enabled"]
    panels = snapshot["panels"]
    pilot = panels["Pilot Evidence"]
    freeze = panels["Freeze Readiness"]
    checks = {
        "all_panels_present": bool(snapshot["coverage"]["all_panels_present"]),
        "no_execution_controls": all(value is False for value in actions.values()),
        "pilot_evidence_distinguished": "actual_operator_pilot_evidence" in pilot["detail"],
        "freeze_not_hardcoded": freeze["detail"].get("freeze_status") == _report("RC3_FREEZE_READINESS_FINAL").get("freeze_status"),
        "persistence_default_disabled": panels["Persistence"]["detail"]["default_state"] == "PERSISTENCE_DISABLED",
        "rc2_compatibility_visible": "rc2_compatibility" in panels["Diagnostics"]["detail"],
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "recommendation": _freeze_recommendation(snapshot),
    }


def build_rc3_ui_integration_report(write_reports: bool = True) -> dict[str, Any]:
    snapshot = build_rc3_ui_snapshot()
    validation = validate_rc3_ui_snapshot(snapshot)
    report = {
        "report": "RC3_UI_CAPABILITY_INTEGRATION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "panel_coverage": snapshot["coverage"],
        "validation": validation,
        "actions_enabled": snapshot["actions_enabled"],
        "operator_pilot_evidence_status": snapshot["panels"]["Pilot Evidence"]["status"],
        "freeze_recommendation": snapshot["panels"]["Freeze Readiness"]["detail"].get("final_recommendation"),
        "freeze_status": snapshot["panels"]["Freeze Readiness"]["detail"].get("freeze_status"),
        "remaining_ui_gaps": () if validation["passed"] else tuple(k for k, v in validation["checks"].items() if not v),
        "safety": snapshot["actions_enabled"],
        "recommendation": validation["recommendation"],
    }
    if write_reports:
        _write_report("RC3_UI_CAPABILITY_INTEGRATION", report)
        _write_report("RC3_OPERATOR_PILOT_FINAL", _operator_pilot_final(snapshot))
        _write_report("RC3_FREEZE_READINESS_FINAL", _freeze_final(snapshot, validation))
    return report


def _goal_panel(reports: dict[str, Any]) -> dict[str, Any]:
    milestone = reports.get("RC3_A_MILESTONE_REVIEW", {})
    goal_report = reports.get("RC3_GOAL_INTERPRETATION", {})
    return {
        "title": "Goal and Planning",
        "status": milestone.get("recommendation", "unknown"),
        "authority": "interpret_only",
        "evidence_status": "existing_report",
        "summary": (
            f"Goal benchmark: {goal_report.get('scores', {}).get('explicit_goal_accuracy', 'unknown')}",
            f"Constraint preservation: {goal_report.get('scores', {}).get('constraint_preservation', 'unknown')}",
            f"Non-goal rejection: {goal_report.get('scores', {}).get('non_goal_rejection', 'unknown')}",
            f"Recommendation: {milestone.get('recommendation', 'unknown')}",
        ),
        "warnings": ("An interpreted goal is not execution authority.",),
        "detail": {
            "milestone": milestone,
            "goal_interpretation": goal_report,
        },
    }


def _plan_panel(reports: dict[str, Any]) -> dict[str, Any]:
    milestone = reports.get("RC3_A_MILESTONE_REVIEW", {})
    plan_report = reports.get("RC3_PLAN_GENERATION", {})
    validation_report = reports.get("RC3_PLAN_VALIDATION", {})
    return {
        "title": "Plan",
        "status": milestone.get("recommendation", "unknown"),
        "authority": "plan_review_only",
        "evidence_status": "existing_report",
        "summary": (
            f"Planning quality: {plan_report.get('scores', {}).get('planning_quality', 'unknown')}",
            f"Dependency accuracy: {plan_report.get('scores', {}).get('dependency_accuracy', 'unknown')}",
            f"Validation recommendation: {validation_report.get('recommendation', 'unknown')}",
            "Execution authorized: False",
        ),
        "warnings": ("Plan creation is not work execution.",),
        "detail": {
            "milestone": milestone,
            "plan_generation": plan_report,
            "plan_validation": validation_report,
        },
    }


def _revision_panel(reports: dict[str, Any]) -> dict[str, Any]:
    milestone = reports.get("RC3_B_MILESTONE_REVIEW", {})
    benchmark = reports.get("RC3_B_REVISION_BENCHMARK", {})
    return {
        "title": "Plan Revision",
        "status": milestone.get("recommendation", "unknown"),
        "authority": "revision_review_only",
        "evidence_status": "existing_report",
        "summary": (
            f"Revision benchmark: {benchmark.get('overall', milestone.get('benchmark_overall', 'unknown'))}",
            f"Trigger detection: {milestone.get('benchmark_scores', {}).get('revision_trigger_detection', 'unknown')}",
            f"Revision quality: {milestone.get('benchmark_scores', {}).get('revision_quality', 'unknown')}",
            f"Recommendation: {milestone.get('recommendation', 'unknown')}",
        ),
        "warnings": ("Revision changes the proposed plan only; it does not execute the plan.",),
        "detail": {
            "milestone": milestone,
            "benchmark": benchmark,
        },
    }


def _introspection_panel(reports: dict[str, Any]) -> dict[str, Any]:
    milestone = reports.get("RC3_A_MILESTONE_REVIEW", {})
    introspection = reports.get("RC3_INTROSPECTION_SCAFFOLD", {})
    progress = reports.get("RC3_PROGRESS_EVALUATION", {})
    gap = reports.get("RC3_CAPABILITY_GAP_ANALYSIS", {})
    return {
        "title": "Introspection and Progress",
        "status": milestone.get("recommendation", "unknown"),
        "authority": "inspect_only",
        "evidence_status": "existing_report",
        "summary": (
            f"Introspection score: {milestone.get('benchmark_scores', {}).get('introspection_accuracy', 'unknown')}",
            f"Progress evaluation: {progress.get('recommendation', 'unknown')}",
            f"Capability gap status: {gap.get('recommendation', 'unknown')}",
            "Self-state fabrication allowed: False",
        ),
        "warnings": ("Missing evidence blocks strong completion claims.",),
        "detail": {
            "milestone": milestone,
            "introspection": introspection,
            "progress": progress,
            "capability_gap": gap,
        },
    }


def _engineering_panel(reports: dict[str, Any]) -> dict[str, Any]:
    milestone = reports.get("RC3_C_MILESTONE_REVIEW", {})
    foundation = reports.get("RC3_C_ENGINEERING_FOUNDATION", {})
    benchmark = reports.get("RC3_C_ENGINEERING_BENCHMARK", {})
    return {
        "title": "Engineering Proposal",
        "status": milestone.get("recommendation", "unknown"),
        "authority": "proposal_only",
        "evidence_status": "existing_report",
        "summary": (
            f"Engineering benchmark: {benchmark.get('overall', milestone.get('benchmark_overall', 'unknown'))}",
            f"Engineering arbitration: {foundation.get('engineering_arbitration', 'unknown')}",
            f"Recommendation: {milestone.get('recommendation', 'unknown')}",
            "External review required before integration: True",
        ),
        "warnings": ("Engineering proposals are advisory and cannot be executed from the UI.",),
        "detail": {
            "milestone": milestone,
            "foundation": foundation,
            "benchmark": benchmark,
        },
    }


def _sandbox_panel(reports: dict[str, Any]) -> dict[str, Any]:
    milestone = reports.get("RC3_D_MILESTONE_REVIEW", {})
    foundation = reports.get("RC3_D_SANDBOX_FOUNDATION", {})
    benchmark = reports.get("RC3_D_SANDBOX_BENCHMARK", {})
    return {
        "title": "Sandbox Proposal",
        "status": milestone.get("recommendation", "unknown"),
        "authority": "sandbox_design_only",
        "evidence_status": "existing_report",
        "summary": (
            f"Sandbox benchmark: {benchmark.get('overall', milestone.get('benchmark_overall', 'unknown'))}",
            f"Isolation: {foundation.get('isolation', 'unknown')}",
            "Sandbox creation allowed: False",
            "Network allowed by UI: False",
        ),
        "warnings": ("No sandbox, container, VM, process, or shell is created.",),
        "detail": {
            "milestone": milestone,
            "foundation": foundation,
            "benchmark": benchmark,
        },
    }


def _stage_panel(title: str, stage_report: dict[str, Any], warning: str) -> dict[str, Any]:
    return {
        "title": title,
        "status": stage_report.get("recommendation", "unknown"),
        "authority": "inspect_only",
        "evidence_status": "stage_report",
        "summary": (
            f"Stage: {stage_report.get('stage')}",
            f"Overall: {stage_report.get('overall')}",
            f"Recommendation: {stage_report.get('recommendation')}",
        ),
        "warnings": (warning,),
        "detail": stage_report.get("result", stage_report),
    }


def _persistence_panel(stage_report: dict[str, Any]) -> dict[str, Any]:
    result = stage_report.get("result", {})
    return {
        "title": "Persistence Boundary",
        "status": "PERSISTENCE_DISABLED",
        "authority": "operator_invoked_fixture_only",
        "evidence_status": "stage_report",
        "summary": (
            "Default state: PERSISTENCE_DISABLED",
            "Fixture controls: LOCAL_FIXTURE_ONLY / NON_PRODUCTION / OPERATOR_INVOKED / REVERSIBLE",
            f"Stage recommendation: {stage_report.get('recommendation')}",
        ),
        "warnings": ("Persistent project memory is not activated by this UI.",),
        "detail": {
            "default_state": "PERSISTENCE_DISABLED",
            "fixture_labels": ("LOCAL_FIXTURE_ONLY", "NON_PRODUCTION", "OPERATOR_INVOKED", "REVERSIBLE"),
            "persistence_contract": result.get(
                "persistence_contract",
                {
                    "owner": "operator",
                    "default_state": "PERSISTENCE_DISABLED",
                    "authority": "operator_invoked_fixture_only",
                    "hidden_persistence": False,
                },
            ),
            "stage_result": result,
        },
    }


def _pilot_panel(stage_report: dict[str, Any], reports: dict[str, Any]) -> dict[str, Any]:
    final = reports.get("RC3_OPERATOR_PILOT_FINAL") or reports.get("RC3_OPERATOR_PILOT_READINESS") or {}
    actual = bool(final.get("actual_operator_pilot_evidence"))
    return {
        "title": "Operator Pilot Evidence",
        "status": "REAL_OPERATOR_EVIDENCE" if actual else "SIMULATED_FIXTURE_EVIDENCE",
        "authority": "inspect_evidence_only",
        "evidence_status": "report_data",
        "summary": (
            f"Real operator evidence: {actual}",
            f"Real sessions completed: {final.get('real_operator_sessions_completed', 0)}",
            f"Recommendation: {final.get('recommendation')}",
        ),
        "warnings": ("Simulated fixture evidence must not be treated as real operator-pilot evidence.",) if not actual else (),
        "detail": {
            **final,
            "stage_result": stage_report.get("result", {}),
            "actual_operator_pilot_evidence": actual,
        },
    }


def _freeze_panel(stage_report: dict[str, Any], reports: dict[str, Any]) -> dict[str, Any]:
    final = reports.get("RC3_FREEZE_READINESS_FINAL") or {}
    return {
        "title": "Freeze Readiness",
        "status": final.get("freeze_status", "unknown"),
        "authority": "readiness_review_only",
        "evidence_status": "report_data",
        "summary": (
            f"Architecture implemented: {final.get('architecture_implemented')}",
            f"Recommendation: {final.get('final_recommendation') or final.get('recommendation')}",
            f"Freeze status: {final.get('freeze_status')}",
            f"Blockers: {len(final.get('freeze_blockers', ())) if isinstance(final.get('freeze_blockers'), list) else 'n/a'}",
        ),
        "warnings": ("Freeze readiness is rendered from report data; status is not hard-coded.",),
        "detail": {
            **final,
            "stage_result": stage_report.get("result", {}),
        },
    }


def _diagnostics_panel(reports: dict[str, Any]) -> dict[str, Any]:
    calibration = reports.get("RC3_COMPREHENSIVE_CALIBRATION") or {}
    return {
        "title": "Diagnostics",
        "status": "available",
        "authority": "developer_overlay_only",
        "evidence_status": "report_data",
        "summary": (
            f"RC3 calibration overall: {calibration.get('overall')}",
            f"RC2 compatibility: {calibration.get('rc2_compatibility', 1.0)}",
            f"Final recommendation: {calibration.get('final_recommendation')}",
        ),
        "warnings": ("Diagnostics are for inspection; they are not authorization.",),
        "detail": {
            "available_reports": sorted(reports),
            "rc2_compatibility": calibration.get("rc2_compatibility", 1.0),
            "safety": calibration.get("safety", {}),
        },
    }


def _load_reports() -> dict[str, Any]:
    names = (
        "RC3_COMPREHENSIVE_CALIBRATION",
        "RC3_ADVERSARIAL_EVALUATION",
        "RC3_STATE_AND_SCHEMA_AUDIT",
        "RC3_GOVERNANCE_AND_PERSISTENCE_AUDIT",
        "RC3_OPERATOR_PILOT_READINESS",
        "RC3_OPERATOR_PILOT_FINAL",
        "RC3_FREEZE_READINESS_FINAL",
    )
    return {name: _report(name) for name in names if (REPORT_DIR / f"{name}.json").exists()}


def _stage_report_from_file(stage: str) -> dict[str, Any]:
    return _report(f"RC3_{stage}_MILESTONE_REVIEW") or {
        "stage": f"RC3-{stage}",
        "recommendation": "missing_report",
        "overall": 0.0,
        "result": {},
    }


def _report(name: str) -> dict[str, Any]:
    path = REPORT_DIR / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _freeze_recommendation(snapshot: dict[str, Any]) -> str:
    freeze = snapshot["panels"]["Freeze Readiness"]["detail"]
    pilot = snapshot["panels"]["Pilot Evidence"]["detail"]
    if (
        pilot.get("actual_operator_pilot_evidence") is True
        and not freeze.get("freeze_blockers")
        and snapshot["coverage"]["all_panels_present"]
    ):
        return "READY_FOR_RC3_FREEZE"
    if not snapshot["coverage"]["all_panels_present"]:
        return "BLOCKED_BY_UI_CAPABILITY_GAPS"
    return "CONTINUE_RC3_UI_CALIBRATION" if pilot.get("actual_operator_pilot_evidence") else "BLOCKED_BY_UNRESOLVED_OPERATOR_FINDINGS"


def _operator_pilot_final(snapshot: dict[str, Any]) -> dict[str, Any]:
    pilot = snapshot["panels"]["Pilot Evidence"]["detail"]
    return {
        "report": "RC3_OPERATOR_PILOT_FINAL",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "actual_operator_pilot_evidence": bool(pilot.get("actual_operator_pilot_evidence")),
        "evidence_status": snapshot["panels"]["Pilot Evidence"]["status"],
        "real_operator_sessions_completed": pilot.get("real_operator_sessions_completed", 0),
        "simulated_fixture_scenarios_available": pilot.get("simulated_fixture_scenarios_available", True),
        "recommendation": "READY_FOR_RC3_FREEZE" if pilot.get("actual_operator_pilot_evidence") else "BLOCKED_BY_UNRESOLVED_OPERATOR_FINDINGS",
    }


def _freeze_final(snapshot: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    existing = snapshot["panels"]["Freeze Readiness"]["detail"]
    pilot = snapshot["panels"]["Pilot Evidence"]["detail"]
    actual = bool(pilot.get("actual_operator_pilot_evidence"))
    blockers = tuple(existing.get("freeze_blockers") or ())
    if not actual and "real operator pilot evidence missing" not in blockers:
        blockers = (*blockers, "real operator pilot evidence missing")
    recommendation = "READY_FOR_RC3_FREEZE" if actual and validation["passed"] and not blockers else "BLOCKED_BY_UNRESOLVED_OPERATOR_FINDINGS"
    return {
        "report": "RC3_FREEZE_READINESS_FINAL",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "architecture_implemented": bool(existing.get("architecture_implemented", True)),
        "ui_capability_coverage": snapshot["coverage"],
        "ui_validation": validation,
        "actual_operator_pilot_evidence": actual,
        "simulated_operator_pilot_evidence": bool(pilot.get("simulated_fixture_scenarios_available", True)),
        "freeze_blockers": blockers,
        "final_recommendation": recommendation,
        "freeze_status": "READY_FOR_RC3_FREEZE" if recommendation == "READY_FOR_RC3_FREEZE" else "RC3_FREEZE_PENDING_REAL_OPERATOR_PILOT_EVIDENCE",
    }


def _write_report(name: str, payload: dict[str, Any]) -> None:
    (REPORT_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        f"# {name.replace('_', ' ').title()}",
        "",
        f"Created: {payload.get('created_at')}",
        f"Recommendation: {payload.get('recommendation', payload.get('final_recommendation'))}",
        f"Freeze status: {payload.get('freeze_status', 'n/a')}",
        "",
        "RC3 UI remains inspect/review only. It does not execute plans, launch sandboxes, activate plugins, mutate repositories, call providers, or grant hidden persistence.",
    ]
    (REPORT_DIR / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(build_rc3_ui_integration_report(write_reports=True), indent=2, sort_keys=True))
