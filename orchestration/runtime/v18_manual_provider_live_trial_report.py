from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v18_manual_provider_live_trial import run_provider_live_trial, validate_provider_live_trial_safe


REPORT_MD = Path("reports/runtime_v18f_manual_provider_live_trial_optional_one_shot.md")
REPORT_JSON = Path("reports/runtime_v18f_manual_provider_live_trial_optional_one_shot.json")


def write_provider_live_trial_report(question: str = "What is a recent fact DELTA cannot know locally?", *, live_provider: bool = False) -> dict[str, object]:
    data = run_provider_live_trial(question, live_provider=live_provider)
    data["all_safe"] = validate_provider_live_trial_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    trace = data["trace"]
    return "\n".join(
        [
            "# Runtime V1.8F - Manual Provider Live Trial Optional One-Shot",
            "",
            f"- Decision: `{trace['decision']['decision']}`",
            f"- Provider call performed: `{trace['decision']['provider_call_performed']}`",
            f"- Key present: `{trace['redacted_request']['api_key_present']}`",
            f"- Key redacted: `{trace['redacted_request']['api_key_redacted']}`",
            f"- All safe: `{data['all_safe']}`",
            "",
            "Default is dry-run. Live provider calls require env gates, key presence, unsupported local question, and explicit `--live-provider`. Provider responses are evidence-only.",
            "",
            f"Final recommendation: `{data['final_recommendation']}`",
            "",
        ]
    )


if __name__ == "__main__":
    result = write_provider_live_trial_report()
    print(f"Runtime V1.8F provider trial: decision={result['trace']['decision']['decision']} final={result['final_recommendation']}")
