from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v22_controlled_general_recall_expansion import run_controlled_general_recall_expansion, validate_recall_expansion_safe


REPORT_MD = Path("reports/runtime_v22b_controlled_general_recall_expansion.md")
REPORT_JSON = Path("reports/runtime_v22b_controlled_general_recall_expansion.json")


def write_recall_expansion_report() -> dict[str, object]:
    payload = run_controlled_general_recall_expansion("What does DELTA know about HYB1?", explain_ranking=True)
    data = {**payload, "all_safe": validate_recall_expansion_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.2B - Controlled General Recall Expansion",
        "",
        "Controlled recall expansion remains candidate-context only and non-authoritative.",
        "",
        f"Candidate count: `{data['candidate_count']}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_recall_expansion_report()
    print(f"Runtime V2.2B recall expansion: safe={result['all_safe']} final={result['final_recommendation']}")
