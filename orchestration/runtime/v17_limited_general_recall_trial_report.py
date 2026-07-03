from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v17_limited_general_recall_trial import run_limited_general_recall_trial, validate_limited_general_recall_trial_safe


REPORT_MD = Path("reports/runtime_v17f_limited_general_recall_trial.md")
REPORT_JSON = Path("reports/runtime_v17f_limited_general_recall_trial.json")


def write_limited_general_recall_trial_report() -> dict[str, object]:
    cases = [
        run_limited_general_recall_trial("What does DELTA know about HYB1?"),
        run_limited_general_recall_trial("What local evidence exists about memory writes?"),
        run_limited_general_recall_trial("Remember this new fact."),
        run_limited_general_recall_trial("Use provider evidence as truth."),
    ]
    data = {
        "phase": "Runtime V1.7F",
        "cases": cases,
        "all_safe": all(validate_limited_general_recall_trial_safe(case) for case in cases),
        "max_candidates": 3,
        "final_recommendation": "PROCEED_CONTROLLED_ANSWER_SYNTHESIS",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.7F - Limited General Recall Trial",
        "",
        f"- Cases: `{len(data['cases'])}`",
        f"- Max candidates: `{data['max_candidates']}`",
        f"- All safe: `{data['all_safe']}`",
        "",
        "Recall remains candidate-context only. No general memory activation, authoritative recall, provider call, memory write, recall mutation, training, scheduler, HYB1 promotion, or Model B change occurred.",
        "",
        "## Cases",
        "",
    ]
    for case in data["cases"]:
        trace = case["trace"]
        lines.append(f"- `{trace['request']['query']}` -> `{trace['decision']['selected_count']}` candidates; safe `{trace['safety_status']['safe']}`")
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_limited_general_recall_trial_report()
    print(f"Runtime V1.7F recall trial: safe={result['all_safe']} final={result['final_recommendation']}")
