from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v24_recall_answer_ux_trial import run_recall_answer_ux_trial, validate_recall_answer_ux_safe


REPORT_MD = Path("reports/runtime_v24c_controlled_recall_answer_ux_trial.md")
REPORT_JSON = Path("reports/runtime_v24c_controlled_recall_answer_ux_trial.json")


def write_recall_answer_ux_report() -> dict[str, object]:
    cases = [run_recall_answer_ux_trial("What does DELTA know about HYB1?"), run_recall_answer_ux_trial("unknown unlikely topic")]
    data = {"phase": "Runtime V2.4C", "cases": cases, "all_safe": all(validate_recall_answer_ux_safe(case) for case in cases), "final_recommendation": "PROCEED_PROVIDER_ASSISTED_UNKNOWN_ANSWER_UX_TRIAL"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.4C - Controlled Recall Answer UX Trial", "", "The recall answer UX displays candidate-context recall with provenance and uncertainty labels.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_recall_answer_ux_report()
    print(f"Runtime V2.4C recall answer UX: safe={result['all_safe']} final={result['final_recommendation']}")

