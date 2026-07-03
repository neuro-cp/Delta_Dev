from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v21_provider_live_trial_user_approved import run_user_approved_provider_live_trial, validate_user_approved_provider_trial_safe


REPORT_MD = Path("reports/runtime_v21c_provider_live_trial_user_approved.md")
REPORT_JSON = Path("reports/runtime_v21c_provider_live_trial_user_approved.json")


def write_provider_live_trial_user_approved_report() -> dict[str, object]:
    payload = run_user_approved_provider_live_trial("What is a recent fact DELTA cannot know locally?")
    data = {**payload, "all_safe": validate_user_approved_provider_trial_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.1C - Provider Live Trial, User-Approved",
        "",
        "Dry-run by default. Live provider calls require exact user approval, env gates, an API key, unsupported local question, and `--live-provider`.",
        "",
        f"Provider call performed: `{data['decision']['provider_call_performed']}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_provider_live_trial_user_approved_report()
    print(f"Runtime V2.1C provider trial: safe={result['all_safe']} final={result['final_recommendation']}")
