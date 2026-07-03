from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v24_evaluator_consolidation_ux_trial import run_evaluator_consolidation_ux_trial, validate_evaluator_consolidation_ux_safe


REPORT_MD = Path("reports/runtime_v24e_evaluator_reviewed_consolidation_ux_trial.md")
REPORT_JSON = Path("reports/runtime_v24e_evaluator_reviewed_consolidation_ux_trial.json")


def write_evaluator_consolidation_ux_report() -> dict[str, object]:
    candidate = {"candidate_id": "candidate-demo", "candidate_text": "Model B remains default.", "provenance_reference_ids": ["v24e-demo"]}
    risky = {**candidate, "candidate_id": "candidate-risk", "ambiguity_flag": True}
    cases = [run_evaluator_consolidation_ux_trial(candidate), run_evaluator_consolidation_ux_trial(risky)]
    data = {"phase": "Runtime V2.4E", "cases": cases, "all_safe": all(validate_evaluator_consolidation_ux_safe(case) for case in cases), "final_recommendation": "PROCEED_V24_SAFETY_CLOSURE"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.4E - Evaluator-Reviewed Consolidation UX Trial", "", "Evaluator consolidation UX displays advisory review only; evaluator output cannot approve, write, delete, or consolidate.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_evaluator_consolidation_ux_report()
    print(f"Runtime V2.4E evaluator consolidation UX: safe={result['all_safe']} final={result['final_recommendation']}")

