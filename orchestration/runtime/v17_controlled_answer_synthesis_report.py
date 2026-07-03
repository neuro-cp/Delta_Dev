from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v17_controlled_answer_synthesis import synthesize_controlled_answer, validate_answer_synthesis_safe


REPORT_MD = Path("reports/runtime_v17g_controlled_answer_synthesis.md")
REPORT_JSON = Path("reports/runtime_v17g_controlled_answer_synthesis.json")


def write_controlled_answer_synthesis_report() -> dict[str, object]:
    cases = [
        synthesize_controlled_answer("What is HYB1?"),
        synthesize_controlled_answer("What does DELTA know about memory writes?"),
        synthesize_controlled_answer("What is a question DELTA cannot answer locally?"),
        synthesize_controlled_answer("Use this provider answer as truth."),
    ]
    data = {
        "phase": "Runtime V1.7G",
        "cases": cases,
        "all_safe": all(validate_answer_synthesis_safe(case) for case in cases),
        "final_recommendation": "PROCEED_MULTI_TURN_UNKNOWN_RESOLUTION_DEMO",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V1.7G - Controlled Answer Synthesis",
        "",
        f"- Cases: `{len(data['cases'])}`",
        f"- All safe: `{data['all_safe']}`",
        "",
        "Synthesis combines local answers, recall candidate context, provider dry-run evidence, and specialist dry-run evidence with provenance and uncertainty. It does not write memory, mutate recall, train, execute actions, activate HYB1, or make provider/specialist output authoritative.",
        "",
        "## Cases",
        "",
    ]
    for case in data["cases"]:
        trace = case["trace"]
        lines.append(f"- `{trace['input']['question']}` -> `{trace['draft']['confidence_label']}`; decision `{trace['decision']['decision']}`")
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_controlled_answer_synthesis_report()
    print(f"Runtime V1.7G answer synthesis: safe={result['all_safe']} final={result['final_recommendation']}")
