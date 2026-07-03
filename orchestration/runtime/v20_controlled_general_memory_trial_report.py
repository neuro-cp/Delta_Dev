from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v20_controlled_general_memory_trial import list_controlled_general_memory_records


REPORT_MD = Path("reports/runtime_v20c_controlled_general_memory_trial_explicit_approval_only.md")
REPORT_JSON = Path("reports/runtime_v20c_controlled_general_memory_trial_explicit_approval_only.json")


def write_controlled_general_memory_trial_report() -> dict[str, object]:
    records = list_controlled_general_memory_records()
    data = {
        "phase": "Runtime V2.0C",
        "records_path": "data/runtime_v20c/controlled_general_memory_records.jsonl",
        "audit_path": "data/runtime_v20c/controlled_general_memory_audit.jsonl",
        "record_count": len(records),
        "approval_required": True,
        "dry_run_default": True,
        "recall_mutated": False,
        "training_triggered": False,
        "provider_direct_write_allowed": False,
        "final_recommendation": "PROCEED_REVIEW_UI_WRITE_APPROVAL_BRIDGE",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.0C - Controlled General Memory Trial, Explicit Approval Only",
        "",
        "Controlled local JSONL memory trial. Writes require exact explicit approval and `--write`; dry-run is default.",
        "",
        f"Record count: `{data['record_count']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_controlled_general_memory_trial_report()
    print(f"Runtime V2.0C controlled memory trial: records={result['record_count']} final={result['final_recommendation']}")
