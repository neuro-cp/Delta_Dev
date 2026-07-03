from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v20_controlled_general_recall_trial import run_controlled_general_recall, validate_controlled_general_recall_safe


REPORT_MD = Path("reports/runtime_v20e_controlled_general_recall_trial.md")
REPORT_JSON = Path("reports/runtime_v20e_controlled_general_recall_trial.json")


def write_controlled_general_recall_trial_report(query: str = "What does DELTA know about HYB1?") -> dict[str, object]:
    payload = run_controlled_general_recall(query)
    data = {**payload, "all_safe": validate_controlled_general_recall_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.0E - Controlled General Recall Trial",
        "",
        "Controlled recall reads approved local trial records as candidate context only. It is not truth, authority, or recall mutation.",
        "",
        f"Candidate count: `{data['candidate_count']}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_controlled_general_recall_trial_report()
    print(f"Runtime V2.0E controlled recall: candidates={result['candidate_count']} final={result['final_recommendation']}")
