from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v23_hyb1_shadow_trial_simulation import APPROVAL_TEXT, run_hyb1_shadow_simulation, validate_hyb1_shadow_simulation_safe


REPORT_MD = Path("reports/runtime_v23a_hyb1_shadow_trial_simulation_opt_in_only.md")
REPORT_JSON = Path("reports/runtime_v23a_hyb1_shadow_trial_simulation_opt_in_only.json")


def write_hyb1_shadow_simulation_report() -> dict[str, object]:
    cases = [
        run_hyb1_shadow_simulation("What does DELTA know about HYB1?"),
        run_hyb1_shadow_simulation("What does DELTA know about HYB1?", approval_text=APPROVAL_TEXT, env={"DELTA_HYB1_SHADOW_TRIAL_ENABLED": "true", "DELTA_HYB1_SHADOW_TRIAL_ALLOW_EXECUTION": "true"}),
    ]
    data = {"phase": "Runtime V2.3A", "cases": cases, "all_safe": all(validate_hyb1_shadow_simulation_safe(case) for case in cases), "final_recommendation": "PROCEED_LOCALHOST_WRITE_EXECUTION_BRIDGE"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.3A - HYB1 Shadow Trial Simulation, Opt-In Only", "", "HYB1 shadow simulation is comparison-only and cannot promote HYB1 or change Model B default.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_hyb1_shadow_simulation_report()
    print(f"Runtime V2.3A HYB1 shadow simulation: safe={result['all_safe']} final={result['final_recommendation']}")

