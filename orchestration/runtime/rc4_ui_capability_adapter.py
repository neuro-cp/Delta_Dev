"""Read-only RC4 UI capability adapter."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc4_governed_action_runtime import RC4_STAGE_REPORTS, run_all_rc4_reports

REPORT_DIR = ROOT / "reports"

RC4_PANEL_ORDER = (
    "Authorization",
    "Repository Intelligence",
    "Candidate Patch",
    "Controlled Execution",
    "Repair and Rollback",
    "Integration Candidate",
    "Tool Orchestration",
    "Adversarial Evaluation",
    "Pilot Evidence",
    "Freeze Readiness",
)

RC4_SAFETY_WARNING = (
    "RC4 UI is inspect/review only. It does not grant authority, execute plans, "
    "create live mutations, push, merge, deploy, activate plugins, call providers, or access protected repositories."
)


def build_rc4_ui_snapshot(*, refresh_reports: bool = False) -> dict[str, Any]:
    if refresh_reports:
        run_all_rc4_reports(write_reports=True)
    reports = _load_reports()
    panels = {
        "Authorization": _panel("Authorization", reports["RC4_AUTHORIZATION_BENCHMARK"], "authority_gate"),
        "Repository Intelligence": _panel("Repository Intelligence", reports["RC4_CODE_INTELLIGENCE_BENCHMARK"], "read_only"),
        "Candidate Patch": _panel("Candidate Patch", reports["RC4_PATCH_GENERATION_BENCHMARK"], "artifact_only"),
        "Controlled Execution": _panel("Controlled Execution", reports["RC4_SANDBOX_EXECUTION_BENCHMARK"], "temporary_workspace_only"),
        "Repair and Rollback": _panel("Repair and Rollback", reports["RC4_REPAIR_AND_ROLLBACK_BENCHMARK"], "fixture_recovery_only"),
        "Integration Candidate": _integration_panel(reports),
        "Tool Orchestration": _panel("Tool Orchestration", reports["RC4_TOOL_ORCHESTRATION_BENCHMARK"], "bounded_tool_contracts"),
        "Adversarial Evaluation": _panel("Adversarial Evaluation", reports["RC4_ADVERSARIAL_EVALUATION"], "negative_case_review"),
        "Pilot Evidence": _pilot_panel(reports),
        "Freeze Readiness": _freeze_panel(reports),
    }
    return {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "panel_order": RC4_PANEL_ORDER,
        "panels": panels,
        "coverage": {
            "panel_count": len(panels),
            "expected_panel_count": len(RC4_PANEL_ORDER),
            "all_panels_present": all(name in panels for name in RC4_PANEL_ORDER),
            "missing_panels": tuple(name for name in RC4_PANEL_ORDER if name not in panels),
        },
        "actions_enabled": {
            "live_repository_mutation": False,
            "sandbox_creation_from_ui": False,
            "provider_call": False,
            "plugin_activation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "deployment": False,
            "protected_repository_interaction": False,
        },
        "safety_warning": RC4_SAFETY_WARNING,
        "reports": reports,
    }


def render_rc4_panel(panel_name: str, snapshot: dict[str, Any] | None = None) -> str:
    snapshot = snapshot or build_rc4_ui_snapshot()
    panel = snapshot["panels"].get(panel_name)
    if not panel:
        return f"Unknown RC4 panel: {panel_name}"
    lines = [
        str(panel["title"]),
        "",
        f"Status: {panel.get('status', 'unknown')}",
        f"Authority: {panel.get('authority', 'inspect_only')}",
        "",
        "Summary:",
    ]
    lines.extend(f"- {item}" for item in panel.get("summary", ()))
    warnings = panel.get("warnings", ())
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in warnings)
    lines.extend(["", "Detail:", json.dumps(panel.get("detail", {}), indent=2, sort_keys=True)[:6000]])
    lines.extend(["", "Safety:", f"- {snapshot['safety_warning']}"])
    return "\n".join(lines)


def validate_rc4_ui_snapshot(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = snapshot or build_rc4_ui_snapshot()
    checks = {
        "all_panels_present": snapshot["coverage"]["all_panels_present"],
        "no_action_controls": all(value is False for value in snapshot["actions_enabled"].values()),
        "pilot_evidence_distinguished": "actual_operator_pilot_evidence" in snapshot["panels"]["Pilot Evidence"]["detail"],
        "freeze_not_overstated": snapshot["panels"]["Freeze Readiness"]["detail"].get("freeze_status") != "RC4_FROZEN_AS_GOVERNED_ACTION_RUNTIME",
        "temporary_execution_label_visible": "CONTROLLED_TEMPORARY_WORKSPACE_EXECUTION" in json.dumps(snapshot["panels"]["Controlled Execution"]),
    }
    recommendation = snapshot["panels"]["Freeze Readiness"]["detail"].get("recommendation", "CONTINUE_RC4_CALIBRATION")
    return {"checks": checks, "passed": all(checks.values()), "recommendation": recommendation}


def build_rc4_ui_integration_report(write_reports: bool = True) -> dict[str, Any]:
    snapshot = build_rc4_ui_snapshot(refresh_reports=False)
    validation = validate_rc4_ui_snapshot(snapshot)
    report = {
        "report": "RC4_UI_CAPABILITY_INTEGRATION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "validation": validation,
        "panel_coverage": snapshot["coverage"],
        "actions_enabled": snapshot["actions_enabled"],
        "freeze_status": snapshot["panels"]["Freeze Readiness"]["detail"].get("freeze_status"),
        "recommendation": validation["recommendation"],
        "safety": snapshot["actions_enabled"],
    }
    if write_reports:
        _write_report("RC4_UI_CAPABILITY_INTEGRATION", report)
    return report


def _panel(title: str, report: dict[str, Any], authority: str) -> dict[str, Any]:
    return {
        "title": title,
        "status": "passed" if report.get("passed") else "needs_review",
        "authority": authority,
        "summary": (
            f"Report: {report.get('report')}",
            f"Passed: {report.get('passed')}",
            f"Score: {report.get('score', 'n/a')}",
        ),
        "warnings": ("Inspectable evidence only; no UI authority is granted.",),
        "detail": report,
    }


def _integration_panel(reports: dict[str, Any]) -> dict[str, Any]:
    execution = reports["RC4_SANDBOX_EXECUTION_BENCHMARK"]
    episode = execution.get("episode", {})
    candidate = episode.get("integration_candidate", {})
    return {
        "title": "Integration Candidate",
        "status": candidate.get("permission_status", {}).get("push", "disabled"),
        "authority": "review_only",
        "summary": (
            f"Candidate: {candidate.get('candidate_id', 'report-derived')}",
            f"Commit permission: {candidate.get('permission_status', {}).get('commit', 'fixture_only')}",
            f"Push permission: {candidate.get('permission_status', {}).get('push', 'disabled')}",
            f"Deploy permission: {candidate.get('permission_status', {}).get('deploy', 'disabled')}",
        ),
        "warnings": ("Integration candidate packaging is not push, merge, or deployment authority.",),
        "detail": candidate,
    }


def _pilot_panel(reports: dict[str, Any]) -> dict[str, Any]:
    report = reports["RC4_OPERATOR_PILOT_READINESS"]
    return {
        "title": "Operator Pilot Evidence",
        "status": report.get("evidence_class", "unknown"),
        "authority": "pilot_review_only",
        "summary": (
            f"Evidence class: {report.get('evidence_class')}",
            f"Actual operator evidence: {report.get('actual_operator_pilot_evidence')}",
            f"Real sessions: {report.get('real_operator_sessions_completed')}",
            f"Recommendation: {report.get('recommendation')}",
        ),
        "warnings": ("Developer rehearsal evidence is not real operator-pilot evidence.",),
        "detail": report,
    }


def _freeze_panel(reports: dict[str, Any]) -> dict[str, Any]:
    report = reports["RC4_FREEZE_READINESS_FINAL"]
    return {
        "title": "Freeze Readiness",
        "status": report.get("freeze_status", "unknown"),
        "authority": "readiness_review_only",
        "summary": (
            f"Freeze status: {report.get('freeze_status')}",
            f"Recommendation: {report.get('recommendation')}",
            f"Blockers: {len(report.get('freeze_blockers', ())) if isinstance(report.get('freeze_blockers'), list) else 'n/a'}",
        ),
        "warnings": ("RC4 is not frozen unless real operator evidence and all criteria are present.",),
        "detail": report,
    }


def _load_reports() -> dict[str, Any]:
    reports = {}
    for name in (*RC4_STAGE_REPORTS, "RC4_CONSOLIDATED_BENCHMARK"):
        path = REPORT_DIR / f"{name}.json"
        if path.exists():
            reports[name] = json.loads(path.read_text(encoding="utf-8"))
        else:
            reports[name] = {"report": name, "passed": False, "recommendation": "MISSING_REPORT"}
    return reports


def _write_report(name: str, data: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"{name}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORT_DIR / f"{name}.md").write_text(
        f"# {name.replace('_', ' ')}\n\n```json\n{json.dumps(data, indent=2, sort_keys=True)}\n```\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    print(json.dumps(build_rc4_ui_integration_report(write_reports=True), indent=2, sort_keys=True))
