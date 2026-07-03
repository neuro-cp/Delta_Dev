"""Runtime V3.0 selected cleanup review.

This module converts existing architecture-audit recommendations into a
report-only cleanup plan. It does not delete files or change runtime behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants


REPORT_MD = Path("reports/runtime_v30e_selected_cleanup_review.md")
REPORT_JSON = Path("reports/runtime_v30e_selected_cleanup_review.json")
AUDIT_JSON = Path("reports/runtime_v28e_architecture_audit.json")


def build_cleanup_review() -> dict[str, object]:
    audit = {}
    if AUDIT_JSON.exists():
        audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    recommendations = list(audit.get("cleanup_recommendations", []))
    legacy_samples = list(audit.get("sample_legacy_scaffolds", []))[:10]
    duplicate_count = int(audit.get("duplicate_filename_count", 0) or 0)
    report_generator_count = int(audit.get("report_generator_count", 0) or 0)
    plan = {
        "safe_cleanup_now": [
            "Consolidate repeated V2.x safety text into shared report helpers in a future focused cleanup.",
            "Prefer shared V3 formatting/explanation helpers for new local interaction reports.",
        ],
        "risky_cleanup_later": [
            "Archiving V1/V14 scaffolds requires compatibility review because many tests and continuation docs still reference them.",
            "Removing duplicate report writers should wait for a dedicated dependency map.",
        ],
        "preserve_for_compatibility": legacy_samples,
        "obsolete_but_referenced": [
            "Older V1/V14 runtime scaffolds appear obsolete for live behavior but remain useful as historical fixtures and regression anchors."
        ],
        "duplicate_logic": [
            f"Architecture audit found {duplicate_count} duplicate filename groups.",
            f"Architecture audit found {report_generator_count} report-generator-like files.",
        ],
    }
    return {
        "phase": "Runtime V3.0E",
        "cleanup_performed": False,
        "source_audit": AUDIT_JSON.as_posix(),
        "audit_recommendations": recommendations,
        "cleanup_plan": plan,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_V30_SAFETY_CHECKPOINT_AND_CONTINUATION",
    }


def write_cleanup_review_report() -> dict[str, object]:
    data = build_cleanup_review()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    plan = data["cleanup_plan"]
    lines = ["# Runtime V3.0E Selected Cleanup Review", "", "Cleanup performed: `False`", ""]
    for section in ("safe_cleanup_now", "risky_cleanup_later", "preserve_for_compatibility", "obsolete_but_referenced", "duplicate_logic"):
        lines.append(f"## {section}")
        lines.append("")
        lines.extend(f"- {item}" for item in plan[section])
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return data


if __name__ == "__main__":
    print(write_cleanup_review_report()["final_recommendation"])
