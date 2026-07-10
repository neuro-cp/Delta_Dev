"""Read-only RC5 developmental cognition UI adapter."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc5_developmental_cognition import RC5_REPORTS, run_all_rc5_reports

REPORT_DIR = ROOT / "reports"

RC5_PANEL_ORDER = (
    "Purpose",
    "Self Evaluation",
    "Deficits",
    "Acquisition",
    "Manual Consultation",
    "Upgrade Handoff",
    "Comparative Evaluation",
    "Developmental Memory",
    "Mimic Calibration",
    "Pilot Evidence",
    "Freeze Readiness",
)

RC5_SAFETY_WARNING = (
    "RC5 UI is inspect/review only. It does not call GPT, call providers, mutate purpose, "
    "write developmental memory, self-approve upgrades, bypass RC4, or run automatic development loops."
)


def build_rc5_ui_snapshot(*, refresh_reports: bool = False) -> dict[str, Any]:
    if refresh_reports:
        run_all_rc5_reports(write_reports=True)
    reports = _load_reports()
    panels = {
        "Purpose": _panel("Purpose Constitution", reports["RC5_PURPOSE_CONSTITUTION_BENCHMARK"], "operator_owned"),
        "Self Evaluation": _panel("Self Evaluation", reports["RC5_SELF_EVALUATION_BENCHMARK"], "read_only_evaluation"),
        "Deficits": _panel("Deficit Detection", reports["RC5_DEFICIT_DETECTION_BENCHMARK"], "hypothesis_only"),
        "Acquisition": _panel("Acquisition Strategy", reports["RC5_ACQUISITION_STRATEGY_BENCHMARK"], "proposal_only"),
        "Manual Consultation": _consultation_panel(reports),
        "Upgrade Handoff": _panel("RC4 Upgrade Handoff", reports["RC5_UPGRADE_HANDOFF_BENCHMARK"], "rc4_handoff_required"),
        "Comparative Evaluation": _panel("Comparative Evaluation", reports["RC5_POST_UPGRADE_EVALUATION_BENCHMARK"], "fixture_evaluation_only"),
        "Developmental Memory": _panel("Developmental Memory Audit", reports["RC5_DEVELOPMENTAL_MEMORY_AUDIT"], "review_required"),
        "Mimic Calibration": _mimic_panel(),
        "Pilot Evidence": _pilot_panel(reports),
        "Freeze Readiness": _freeze_panel(reports),
    }
    return {
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "panel_order": RC5_PANEL_ORDER,
        "panels": panels,
        "coverage": {
            "panel_count": len(panels),
            "expected_panel_count": len(RC5_PANEL_ORDER),
            "all_panels_present": all(name in panels for name in RC5_PANEL_ORDER),
            "missing_panels": tuple(name for name in RC5_PANEL_ORDER if name not in panels),
        },
        "actions_enabled": {
            "gpt_api_call": False,
            "provider_call": False,
            "automatic_consultation": False,
            "purpose_mutation": False,
            "upgrade_self_approval": False,
            "rc4_authorization_bypass": False,
            "developmental_memory_auto_write": False,
            "automatic_development_loop": False,
            "protected_repository_interaction": False,
        },
        "safety_warning": RC5_SAFETY_WARNING,
        "reports": reports,
    }


def render_rc5_panel(panel_name: str, snapshot: dict[str, Any] | None = None) -> str:
    snapshot = snapshot or build_rc5_ui_snapshot()
    panel = snapshot["panels"].get(panel_name)
    if not panel:
        return f"Unknown RC5 panel: {panel_name}"
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
    lines.extend(["", "Detail:", json.dumps(panel.get("detail", {}), indent=2, sort_keys=True)[:7000]])
    lines.extend(["", "Safety:", f"- {snapshot['safety_warning']}"])
    return "\n".join(lines)


def validate_rc5_ui_snapshot(snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = snapshot or build_rc5_ui_snapshot()
    panels = snapshot["panels"]
    actions = snapshot["actions_enabled"]
    checks = {
        "all_panels_present": snapshot["coverage"]["all_panels_present"],
        "no_action_controls": all(value is False for value in actions.values()),
        "manual_transport_visible": "manual" in json.dumps(panels["Manual Consultation"]).lower(),
        "freeze_not_overstated": panels["Freeze Readiness"]["detail"].get("freeze_status") != "RC5_FROZEN",
        "pilot_evidence_distinguished": panels["Pilot Evidence"]["detail"].get("actual_operator_pilot_evidence") is False,
        "rc4_handoff_required": "rc4_handoff" in json.dumps(panels["Upgrade Handoff"]).lower(),
        "mimic_not_real_pilot": panels["Mimic Calibration"]["detail"].get("evidence_class") in {None, "DEVELOPER_REHEARSAL_EVIDENCE"},
    }
    recommendation = panels["Freeze Readiness"]["detail"].get("recommendation", "CONTINUE_RC5_CALIBRATION")
    return {"checks": checks, "passed": all(checks.values()), "recommendation": recommendation}


def build_rc5_ui_integration_report(write_reports: bool = True) -> dict[str, Any]:
    snapshot = build_rc5_ui_snapshot(refresh_reports=False)
    validation = validate_rc5_ui_snapshot(snapshot)
    report = {
        "report": "RC5_UI_CAPABILITY_INTEGRATION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "validation": validation,
        "panel_coverage": snapshot["coverage"],
        "actions_enabled": snapshot["actions_enabled"],
        "freeze_status": snapshot["panels"]["Freeze Readiness"]["detail"].get("freeze_status"),
        "recommendation": validation["recommendation"],
        "safety": snapshot["actions_enabled"],
    }
    if write_reports:
        _write_report("RC5_UI_CAPABILITY_INTEGRATION", report)
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
            f"Recommendation: {report.get('recommendation', 'n/a')}",
        ),
        "warnings": ("Inspectable evidence only; no UI authority is granted.",),
        "detail": report,
    }


def _consultation_panel(reports: dict[str, Any]) -> dict[str, Any]:
    report = reports["RC5_CONSULTATION_COMPRESSION_BENCHMARK"]
    return {
        "title": "Manual Consultation Bridge",
        "status": "manual_transport_only" if report.get("passed") else "needs_review",
        "authority": "advisory_only",
        "summary": (
            f"Packet compact: {report.get('checks', {}).get('packet_compact')}",
            f"Manual transport: {report.get('checks', {}).get('manual_transport')}",
            f"Unsafe advice rejected: {report.get('checks', {}).get('unsafe_rejected')}",
            "No API transport is enabled.",
        ),
        "warnings": ("GPT/API escalation is not wired here; packets are copied by an operator if used.",),
        "detail": report,
    }


def _pilot_panel(reports: dict[str, Any]) -> dict[str, Any]:
    report = reports["RC5_OPERATOR_PILOT_READINESS"]
    return {
        "title": "Operator Pilot Evidence",
        "status": report.get("evidence_class", "unknown"),
        "authority": "pilot_review_only",
        "summary": (
            f"Evidence class: {report.get('evidence_class')}",
            f"Actual operator evidence: {report.get('actual_operator_pilot_evidence')}",
            f"Recommendation: {report.get('recommendation')}",
        ),
        "warnings": ("Developer rehearsal evidence is not real operator-pilot evidence.",),
        "detail": report,
    }


def _mimic_panel() -> dict[str, Any]:
    path = REPORT_DIR / "RC45_OPERATOR_MIMIC_CONSOLIDATED.json"
    if path.exists():
        report = json.loads(path.read_text(encoding="utf-8"))
    else:
        report = {"report": "RC45_OPERATOR_MIMIC_CONSOLIDATED", "evidence_class": "not_generated", "recommendation": "RUN_OPERATOR_MIMIC_CALIBRATION"}
    return {
        "title": "Operator Mimic Calibration",
        "status": report.get("recommendation", "not_generated"),
        "authority": "developer_rehearsal_only",
        "summary": (
            f"Evidence class: {report.get('evidence_class')}",
            f"Scenarios: {report.get('scenario_count', 'n/a')}",
            f"Integrated cycles: {report.get('integrated_cycle_count', 'n/a')}",
            f"Recommendation: {report.get('recommendation')}",
        ),
        "warnings": ("Mimic calibration is not real operator-pilot evidence and cannot freeze RC4 or RC5.",),
        "detail": report,
    }


def _freeze_panel(reports: dict[str, Any]) -> dict[str, Any]:
    report = reports["RC5_FREEZE_READINESS_FINAL"]
    blockers = report.get("freeze_blockers", ())
    return {
        "title": "Freeze Readiness",
        "status": report.get("freeze_status", "unknown"),
        "authority": "readiness_review_only",
        "summary": (
            f"Freeze status: {report.get('freeze_status')}",
            f"Recommendation: {report.get('recommendation')}",
            f"Blockers: {len(blockers) if isinstance(blockers, list) else 'n/a'}",
        ),
        "warnings": ("RC5 is not frozen unless real operator evidence and all criteria are present.",),
        "detail": report,
    }


def _load_reports() -> dict[str, Any]:
    reports = {}
    for name in (*RC5_REPORTS, "RC5_CONSOLIDATED_BENCHMARK"):
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
    print(json.dumps(build_rc5_ui_integration_report(write_reports=True), indent=2, sort_keys=True))
