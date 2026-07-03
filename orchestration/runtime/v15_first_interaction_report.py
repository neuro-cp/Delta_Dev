from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_first_interaction import (
    RUNTIME_V15D_INVARIANT_FLAGS,
    STARTER_DELTA_QUESTION,
    build_first_interaction_result,
    format_first_interaction_cli_output,
)


REPORT_MD = Path("reports/runtime_v15d_first_live_interaction_path.md")
REPORT_JSON = Path("reports/runtime_v15d_first_live_interaction_path.json")


def build_first_interaction_report_data() -> dict[str, object]:
    starter = build_first_interaction_result(STARTER_DELTA_QUESTION)
    return {
        "phase": "Runtime V1.5D",
        "title": "First Live Interaction Path, Console-Only",
        "status": "first-live-console-interaction-only_no-side-effects_no-memory_no-provider",
        "final_recommendation": "PROCEED_V15E_HYB1_LIMITED_OPT_IN_TRIAL_DESIGN",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v15_first_interaction.py",
            "orchestration/runtime/v15_first_interaction_report.py",
            "scripts/ask_delta.py",
            "tests/runtime_v15/test_v15_first_live_interaction_path.py",
            "reports/runtime_v15d_first_live_interaction_path.md",
            "reports/runtime_v15d_first_live_interaction_path.json",
            "docs/runtime_v15d_first_live_interaction_path_prompt.txt",
        ],
        "starter_question": STARTER_DELTA_QUESTION,
        "starter_result": starter,
        "starter_cli_output": format_first_interaction_cli_output(starter),
        "invariant_flags": dict(RUNTIME_V15D_INVARIANT_FLAGS),
        "test_status": "run py_compile, tests/runtime_v14 tests/runtime_v15, and scripts/ask_delta.py starter question",
    }


def write_first_interaction_report() -> dict[str, object]:
    data = build_first_interaction_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    return (
        "# Runtime V1.5D - First Live Interaction Path, Console-Only\n\n"
        "Runtime V1.5D enables only a one-shot manual console preview path. No provider, tool, action, memory, canonical, recall, training, export, scheduler, or HYB1 default path is active.\n\n"
        f"- Status: `{data['status']}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n"
        f"- Starter question: `{data['starter_question']}`\n\n"
        "## Starter Output\n\n"
        "```text\n"
        f"{data['starter_cli_output']}\n"
        "```\n"
    )


if __name__ == "__main__":
    write_first_interaction_report()
