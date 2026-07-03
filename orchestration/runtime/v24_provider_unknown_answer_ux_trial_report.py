from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v24_provider_unknown_answer_ux_trial import APPROVAL_TEXT, run_provider_unknown_answer_ux_trial, validate_provider_unknown_answer_ux_safe


REPORT_MD = Path("reports/runtime_v24d_provider_assisted_unknown_answer_ux_trial.md")
REPORT_JSON = Path("reports/runtime_v24d_provider_assisted_unknown_answer_ux_trial.json")


def write_provider_unknown_answer_ux_report() -> dict[str, object]:
    cases = [
        run_provider_unknown_answer_ux_trial("What does DELTA know about HYB1?"),
        run_provider_unknown_answer_ux_trial("unknown topic"),
        run_provider_unknown_answer_ux_trial("unknown topic", approval_text=APPROVAL_TEXT, live_provider=True, env={"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test"}, transport=_mock_transport),
    ]
    data = {"phase": "Runtime V2.4D", "cases": cases, "all_safe": all(validate_provider_unknown_answer_ux_safe(case) for case in cases), "final_recommendation": "PROCEED_EVALUATOR_REVIEWED_CONSOLIDATION_UX_TRIAL"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _mock_transport(url, headers, payload, timeout):
    return {"answer_text": "Mock provider evidence only.", "provenance": "mock-v24d", "uncertainty": "unverified"}


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.4D - Provider-Assisted Unknown Answer UX Trial", "", "Provider assistance is gated, evidence-only, redacted, and unavailable for known local questions.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_provider_unknown_answer_ux_report()
    print(f"Runtime V2.4D provider unknown UX: safe={result['all_safe']} final={result['final_recommendation']}")

