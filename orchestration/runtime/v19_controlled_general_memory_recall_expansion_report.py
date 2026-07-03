from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v19_controlled_general_memory_recall_expansion import build_controlled_general_memory_recall_expansion_design, validate_general_memory_expansion_design_safe


REPORT_MD = Path("reports/runtime_v19a_controlled_general_memory_recall_expansion_design.md")
REPORT_JSON = Path("reports/runtime_v19a_controlled_general_memory_recall_expansion_design.json")


def write_general_memory_expansion_report() -> dict[str, object]:
    data = build_controlled_general_memory_recall_expansion_design()
    data["all_safe"] = validate_general_memory_expansion_design_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Runtime V1.9A - Controlled General Memory / Recall Expansion Design",
            "",
            f"- Decision: `{data['decision']['outcome']}`",
            f"- General memory active: `{data['invariant_flags']['general_memory_active']}`",
            f"- Authoritative recall active: `{data['invariant_flags']['authoritative_recall_active']}`",
            f"- All safe: `{data['all_safe']}`",
            "",
            "Design only. Approved canonical records only; rejected, deferred, unapproved, and rolled-back records are excluded. Provider/specialist/evaluator output cannot become memory without candidate plus exact approval.",
            "",
            f"Final recommendation: `{data['final_recommendation']}`",
            "",
        ]
    )


if __name__ == "__main__":
    result = write_general_memory_expansion_report()
    print(f"Runtime V1.9A memory expansion design: safe={result['all_safe']} final={result['final_recommendation']}")
