from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v18_manual_provider_live_trial_gate import check_provider_live_trial_gate, validate_provider_live_trial_gate_safe


REPORT_MD = Path("reports/runtime_v18e_manual_provider_live_trial_gate.md")
REPORT_JSON = Path("reports/runtime_v18e_manual_provider_live_trial_gate.json")


def write_provider_live_trial_gate_report(question: str = "What is a recent fact DELTA cannot know locally?") -> dict[str, object]:
    data = check_provider_live_trial_gate(question)
    data["all_safe"] = validate_provider_live_trial_gate_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Runtime V1.8E - Manual Provider Live Trial Gate",
            "",
            f"- Decision: `{data['decision']['status']}`",
            f"- Requirements passed: `{data['report_entry']['passed_requirements']}/{data['report_entry']['total_requirements']}`",
            f"- Key present: `{data['audit_record']['key_present']}`",
            f"- Key redacted: `{data['audit_record']['key_redacted']}`",
            f"- Provider call performed: `{data['decision']['provider_call_performed']}`",
            f"- All safe: `{data['all_safe']}`",
            "",
            "Gate only. No provider call, memory write, recall mutation, training, action execution, scheduler activation, HYB1 promotion, or Model B change.",
            "",
            f"Final recommendation: `{data['final_recommendation']}`",
            "",
        ]
    )


if __name__ == "__main__":
    result = write_provider_live_trial_gate_report()
    print(f"Runtime V1.8E provider gate: decision={result['decision']['status']} final={result['final_recommendation']}")
