from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v20_local_ux_consolidation import run_delta_ux_command, validate_local_ux_safe


REPORT_MD = Path("reports/runtime_v20a_local_delta_ux_consolidation.md")
REPORT_JSON = Path("reports/runtime_v20a_local_delta_ux_consolidation.json")


def build_local_ux_consolidation_report() -> dict[str, object]:
    samples = {
        "status": run_delta_ux_command("status"),
        "ask": run_delta_ux_command("ask", "What is HYB1?"),
        "recall": run_delta_ux_command("recall", "What does DELTA know about HYB1?"),
        "safety": run_delta_ux_command("safety"),
    }
    return {
        "phase": "Runtime V2.0A",
        "samples": samples,
        "all_safe": all(validate_local_ux_safe(item) for item in samples.values()),
        "commands": ["status", "ask", "recall", "synthesize", "session-start", "session-ask", "session-clear", "review-ui", "quality-ui", "readiness", "provider-dry-run", "evaluator-dry-run", "safety"],
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_MEMORY_TRIAL_DESIGN",
    }


def write_local_ux_consolidation_report() -> dict[str, object]:
    data = build_local_ux_consolidation_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime V2.0A - Local DELTA UX Consolidation",
        "",
        "The local `scripts/delta.py` entrypoint consolidates existing local console, recall, synthesis, review, quality, readiness, provider dry-run, evaluator dry-run, and safety commands.",
        "",
        f"All safe: `{data['all_safe']}`",
        "",
        "## Commands",
        "",
    ]
    lines += [f"- `{item}`" for item in data["commands"]]
    lines += ["", f"Final recommendation: `{data['final_recommendation']}`", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    result = write_local_ux_consolidation_report()
    print(f"Runtime V2.0A local UX consolidation: safe={result['all_safe']} final={result['final_recommendation']}")
