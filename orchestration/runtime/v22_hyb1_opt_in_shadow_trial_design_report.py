from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v22_hyb1_opt_in_shadow_trial_design import design_hyb1_shadow_trial, validate_hyb1_shadow_design_safe


REPORT_MD = Path("reports/runtime_v22e_hyb1_opt_in_shadow_trial_design.md")
REPORT_JSON = Path("reports/runtime_v22e_hyb1_opt_in_shadow_trial_design.json")


def write_hyb1_shadow_design_report() -> dict[str, object]:
    payload = design_hyb1_shadow_trial()
    data = {**payload, "all_safe": validate_hyb1_shadow_design_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.2E - HYB1 Opt-In Shadow Trial Design",
        "",
        "HYB1 shadow trial remains design-only. It does not execute HYB1, promote HYB1, or change Model B defaults.",
        "",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_hyb1_shadow_design_report()
    print(f"Runtime V2.2E HYB1 shadow design: safe={result['all_safe']} final={result['final_recommendation']}")
