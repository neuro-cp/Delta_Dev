from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v24_memory_write_ux_trial import build_memory_write_approval, run_memory_write_ux_trial, validate_memory_write_ux_safe


REPORT_MD = Path("reports/runtime_v24b_controlled_memory_write_ux_trial.md")
REPORT_JSON = Path("reports/runtime_v24b_controlled_memory_write_ux_trial.json")


def write_memory_write_ux_report() -> dict[str, object]:
    candidate = {"candidate_id": "memory-candidate-demo", "proposed_memory_text": "Model B remains default.", "provenance_reference_ids": ["v24b-demo"]}
    cases = [run_memory_write_ux_trial(candidate), run_memory_write_ux_trial(candidate, build_memory_write_approval("memory-candidate-demo"), write=False)]
    data = {"phase": "Runtime V2.4B", "cases": cases, "all_safe": all(validate_memory_write_ux_safe(case) for case in cases), "final_recommendation": "PROCEED_CONTROLLED_RECALL_ANSWER_UX_TRIAL"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.4B - Controlled Memory Write UX Trial", "", "The memory write UX guides exact structured approval and delegates to controlled trial logic only.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_memory_write_ux_report()
    print(f"Runtime V2.4B memory write UX: safe={result['all_safe']} final={result['final_recommendation']}")

