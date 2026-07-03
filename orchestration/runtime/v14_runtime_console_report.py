from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v14_runtime_console import (
    RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS,
    build_runtime_console_preview,
    create_runtime_console_plan,
)


REPORT_MD = Path("reports/runtime_ui_minimal_message_console.md")
REPORT_JSON = Path("reports/runtime_ui_minimal_message_console.json")


def build_runtime_console_report_data() -> dict[str, object]:
    preview = build_runtime_console_preview(
        "Please preview how DELTA would inspect this message without learning or executing anything.",
        source_reference="manual-console-report-demo",
    )
    plan = create_runtime_console_plan((preview,))
    return {
        "phase": "Runtime V1.4R",
        "title": "Minimal Runtime UI / Message Console",
        "status": "manual_review_only_no_provider_no_mutation_no_execution",
        "final_recommendation": "PROCEED_MANUAL_END_TO_END_MESSAGE_TESTING",
        "implementation_choice": "CLI/script console",
        "current_default": "Model B remains default; HYB1 remains dormant/env-gated",
        "files_added": [
            "orchestration/runtime/v14_runtime_console.py",
            "orchestration/runtime/v14_runtime_console_report.py",
            "scripts/runtime_console.py",
            "tests/runtime_v14/test_v14_runtime_console.py",
            "reports/runtime_ui_minimal_message_console.md",
            "reports/runtime_ui_minimal_message_console.json",
            "docs/runtime_ui_minimal_message_console_prompt.txt",
        ],
        "design_summary": (
            "Manual local console preview creates review-only RawExperienceInput, ExperienceRecord, "
            "StructuralInputUnit, SemanticFrame, SemanticSignal, trace summary, and disabled capability status."
        ),
        "pipeline_preview_summary": (
            "manual user message -> raw experience preview -> bounded experience record -> "
            "structural semantic preview -> trace summary -> safety flag display"
        ),
        "disabled_capability_flags": dict(RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS),
        "preview": preview.as_dict(),
        "plan": plan.as_dict(),
        "safety_boundaries": [
            "message console is not autonomous agent",
            "user message is not automatic training example",
            "runtime preview is not runtime mutation",
            "trace display is not memory write",
            "disabled capability flag is not capability activation",
            "UI or CLI command is not execution authority",
            "manual inspection is not background ingestion",
        ],
        "inactive_systems": [
            "provider calls",
            "specialist routing",
            "training",
            "fine-tuning",
            "canonical writes",
            "memory mutation",
            "runtime recall mutation",
            "recall bridge activation",
            "action execution",
            "tool calls",
            "file/network/database side effects",
            "background listeners",
            "schedulers/daemons/workers/timers/queues",
            "automatic ingestion",
        ],
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_runtime_console_report() -> dict[str, object]:
    data = build_runtime_console_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Minimal Runtime UI / Message Console",
        "",
        "## Summary",
        "",
        "This phase adds a minimal local manual message console scaffold. It previews inert runtime trace objects and disabled capability flags without provider calls, memory writes, training, recall mutation, action execution, tool calls, or side effects.",
        "",
        f"- Status: `{data['status']}`",
        f"- Implementation choice: `{data['implementation_choice']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Current default: {data['current_default']}",
        "",
        "## Pipeline Preview",
        "",
        str(data["pipeline_preview_summary"]),
        "",
        "## Safety Boundaries",
        "",
    ]
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(["", "## Inactive Systems", ""])
    lines.extend(f"- {item}" for item in data["inactive_systems"])
    lines.extend(["", "## Disabled Capability Flags", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["disabled_capability_flags"].items())
    lines.extend(
        [
            "",
            "## Test Status",
            "",
            str(data["test_status"]),
            "",
            "## Continuation Checkpoint",
            "",
            "The runtime console is manual, local, deterministic, and review-only. It does not add provider/tool calls, specialist routing, action execution, memory/canonical mutation, recall mutation, training, background ingestion, schedulers, or runtime default changes.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_runtime_console_report()
