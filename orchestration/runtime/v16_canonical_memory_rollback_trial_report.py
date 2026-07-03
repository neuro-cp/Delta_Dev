from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_canonical_memory_rollback_trial import execute_canonical_memory_rollback_trial, validate_rollback_trial_safe


REPORT_MD = Path("reports/runtime_v16j_canonical_memory_rollback_trial.md")
REPORT_JSON = Path("reports/runtime_v16j_canonical_memory_rollback_trial.json")


def write_rollback_trial_report(canonical_record_id: str = "v15i-canonical-trial-record-f97e30a731f4638c") -> dict[str, object]:
    data = execute_canonical_memory_rollback_trial(canonical_record_id, dry_run=True)
    data["rollback_safe"] = validate_rollback_trial_safe(data)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V1.6J - Canonical Memory Rollback Trial\n\n"
        f"- Rollback safe: `{data['rollback_safe']}`\n"
        f"- Decision: `{data['decision']['decision']}`\n"
        f"- Marker written: `{data['decision']['marker_written']}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n\n"
        "Dry-run only by default. Original records are preserved; no deletion, provider call, action execution, training, or recall mutation occurs.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    report = write_rollback_trial_report()
    print(f"Runtime V1.6J rollback trial: safe={report['rollback_safe']} decision={report['decision']['decision']} final={report['final_recommendation']}")
