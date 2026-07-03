from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v21_controlled_general_memory_expansion import (
    approval_text_for_candidate,
    list_expanded_memory_candidates,
    run_expanded_memory_write_trial,
    validate_memory_expansion_safe,
)


REPORT_MD = Path("reports/runtime_v21b_controlled_general_memory_trial_expansion.md")
REPORT_JSON = Path("reports/runtime_v21b_controlled_general_memory_trial_expansion.json")


def write_memory_expansion_report() -> dict[str, object]:
    candidates = list_expanded_memory_candidates()
    dry_run = run_expanded_memory_write_trial("memory-candidate-demo", approval_text_for_candidate("memory-candidate-demo"))
    blocked = run_expanded_memory_write_trial("ambiguous-candidate-demo", approval_text_for_candidate("ambiguous-candidate-demo"))
    data = {
        "phase": "Runtime V2.1B",
        "candidates": candidates,
        "dry_run_decision": dry_run,
        "blocked_decision": blocked,
        "all_safe": validate_memory_expansion_safe(dry_run) and validate_memory_expansion_safe(blocked),
        "final_recommendation": "PROCEED_PROVIDER_LIVE_TRIAL_USER_APPROVED",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.1B - Controlled General Memory Trial Expansion",
        "",
        "Expanded controlled general memory trial support across multiple candidate sources. Explicit approval remains required and dry-run remains default.",
        "",
        f"Candidate sources: `{len(data['candidates'])}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_memory_expansion_report()
    print(f"Runtime V2.1B memory expansion: safe={result['all_safe']} final={result['final_recommendation']}")
