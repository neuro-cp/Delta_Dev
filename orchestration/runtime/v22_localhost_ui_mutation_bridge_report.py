from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v22_localhost_ui_mutation_bridge import (
    LocalhostUIEventKind,
    run_ui_mutation_bridge,
    validate_ui_mutation_bridge_safe,
)


REPORT_MD = Path("reports/runtime_v22a_localhost_ui_mutation_bridge_explicit_approval_only.md")
REPORT_JSON = Path("reports/runtime_v22a_localhost_ui_mutation_bridge_explicit_approval_only.json")


def write_ui_mutation_bridge_report() -> dict[str, object]:
    cases = [
        run_ui_mutation_bridge("memory-candidate-demo", LocalhostUIEventKind.APPROVE),
        run_ui_mutation_bridge("memory-candidate-demo", LocalhostUIEventKind.REJECT),
        run_ui_mutation_bridge("memory-candidate-demo", LocalhostUIEventKind.DEFER),
    ]
    data = {
        "phase": "Runtime V2.2A",
        "cases": cases,
        "all_safe": all(validate_ui_mutation_bridge_safe(case) for case in cases),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_RECALL_EXPANSION",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.2A - Localhost UI Mutation Bridge, Explicit Approval Only",
        "",
        "The localhost UI bridge creates structured approval/reject/defer export events only. It performs no hidden memory write.",
        "",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_ui_mutation_bridge_report()
    print(f"Runtime V2.2A UI mutation bridge: safe={result['all_safe']} final={result['final_recommendation']}")
