from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_canonical_memory_write_trial import sample_canonical_memory_write_trial_design, validate_canonical_memory_write_trial_safe


REPORT_MD = Path("reports/runtime_v15h_human_approved_canonical_memory_write_trial_design.md")
REPORT_JSON = Path("reports/runtime_v15h_human_approved_canonical_memory_write_trial_design.json")


def build_canonical_memory_write_trial_report_data() -> dict[str, object]:
    design = sample_canonical_memory_write_trial_design()
    return {
        "phase": "Runtime V1.5H",
        "title": "Human-Approved Canonical Memory Write Trial Design",
        "status": "design_only_no_canonical_write_no_recall_no_training",
        "design": design,
        "design_safe": validate_canonical_memory_write_trial_safe(design),
        "final_recommendation": "PROCEED_EXPLICIT_USER_APPROVED_CANONICAL_MEMORY_WRITE_TRIAL_OR_RECALL_BRIDGE_LIMITED_TRIAL_DESIGN",
    }


def write_canonical_memory_write_trial_report() -> dict[str, object]:
    data = build_canonical_memory_write_trial_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    d = data["design"]
    lines = [
        "# Runtime V1.5H - Human-Approved Canonical Memory Write Trial Design",
        "",
        f"- Status: `{data['status']}`",
        f"- Design safe: `{data['design_safe']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        f"- write_enabled: `{d['write_candidate']['write_enabled']}`",
        f"- canonical_write_executed: `{d['write_candidate']['canonical_write_executed']}`",
        f"- approval_present: `{d['approval_gate']['approval_present']}`",
        f"- rollback_executed: `{d['rollback_reference']['rollback_executed']}`",
        f"- recall_triggered: `{d['decision']['recall_triggered']}`",
        f"- training_triggered: `{d['decision']['training_triggered']}`",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_canonical_memory_write_trial_report()
    print(f"Runtime V1.5H Canonical Write Trial Design: safe={report['design_safe']} final={report['final_recommendation']}")
