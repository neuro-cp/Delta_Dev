from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v20_controlled_general_memory_trial_design import (
    MemoryCandidateState,
    design_controlled_general_memory_trial,
    validate_controlled_general_memory_design_safe,
)


REPORT_MD = Path("reports/runtime_v20b_controlled_general_memory_trial_design.md")
REPORT_JSON = Path("reports/runtime_v20b_controlled_general_memory_trial_design.json")


def write_controlled_general_memory_trial_design_report() -> dict[str, object]:
    cases = [
        design_controlled_general_memory_trial("candidate-approved", MemoryCandidateState.APPROVED),
        design_controlled_general_memory_trial("candidate-rejected", MemoryCandidateState.REJECTED),
        design_controlled_general_memory_trial("provider-output", MemoryCandidateState.APPROVED, source_kind="provider_output"),
    ]
    data = {
        "phase": "Runtime V2.0B",
        "cases": cases,
        "all_safe": all(validate_controlled_general_memory_design_safe(case) for case in cases),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_EXPLICIT_APPROVAL_ONLY",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.0B - Controlled General Memory Trial Design",
        "",
        "Design-only controlled general memory trial policy. It performs no write and does not activate general recall.",
        "",
        f"All safe: `{data['all_safe']}`",
        "",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_controlled_general_memory_trial_design_report()
    print(f"Runtime V2.0B controlled general memory design: safe={result['all_safe']} final={result['final_recommendation']}")
