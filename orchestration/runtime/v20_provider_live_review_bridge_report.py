from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v20_provider_live_review_bridge import build_provider_live_review_bridge, validate_provider_live_review_bridge_safe


REPORT_MD = Path("reports/runtime_v20f_provider_evidence_live_trial_review_bridge.md")
REPORT_JSON = Path("reports/runtime_v20f_provider_evidence_live_trial_review_bridge.json")


def write_provider_live_review_bridge_report() -> dict[str, object]:
    payload = build_provider_live_review_bridge()
    data = {**payload, "all_safe": validate_provider_live_review_bridge_safe(payload)}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.0F - Provider Evidence Live Trial Review Bridge",
        "",
        "Provider evidence, if present, is bridged into review as evidence-only and non-authoritative. No live call is performed by this bridge.",
        "",
        f"Provider report present: `{data['provider_report_present']}`",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_provider_live_review_bridge_report()
    print(f"Runtime V2.0F provider bridge: safe={result['all_safe']} final={result['final_recommendation']}")
