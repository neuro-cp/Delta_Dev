from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v21_provider_live_trial_user_approved import APPROVAL_TEXT as LIVE_APPROVAL_TEXT
from orchestration.runtime.v23_provider_live_to_candidate_trial import CONVERSION_APPROVAL_TEXT, run_provider_live_to_candidate_trial, validate_provider_live_to_candidate_safe


REPORT_MD = Path("reports/runtime_v23d_provider_evidence_live_to_candidate_trial_user_approved.md")
REPORT_JSON = Path("reports/runtime_v23d_provider_evidence_live_to_candidate_trial_user_approved.json")


def write_provider_live_to_candidate_report() -> dict[str, object]:
    cases = [
        run_provider_live_to_candidate_trial("unknown topic", live_provider=False),
        run_provider_live_to_candidate_trial("unknown topic", live_provider=True, live_approval_text=LIVE_APPROVAL_TEXT, conversion_approval_text=CONVERSION_APPROVAL_TEXT, env={"DELTA_UNKNOWN_PROVIDER_ENABLED": "true", "DELTA_UNKNOWN_PROVIDER_ALLOW_LIVE_CALL": "true", "DELTA_UNKNOWN_PROVIDER_API_KEY": "test-key"}, transport=_mock_transport),
    ]
    data = {"phase": "Runtime V2.3D", "cases": cases, "all_safe": all(validate_provider_live_to_candidate_safe(case) for case in cases), "final_recommendation": "PROCEED_DAILY_EVALUATOR_SCHEDULED_DRY_RUN_TRIAL"}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _mock_transport(url, headers, payload, timeout):
    return {"answer_text": "Mocked provider evidence says this topic requires review.", "provenance": "mocked-v23d-provider", "uncertainty": "mocked unverified evidence"}


def _render(data: dict[str, object]) -> str:
    return "\n".join(("# Runtime V2.3D - Provider Evidence Live-to-Candidate Trial, User-Approved", "", "Provider evidence may become a candidate proposal only. It does not write memory or become truth.", "", f"All safe: `{data['all_safe']}`", f"Final recommendation: `{data['final_recommendation']}`", ""))


if __name__ == "__main__":
    result = write_provider_live_to_candidate_report()
    print(f"Runtime V2.3D provider-to-candidate: safe={result['all_safe']} final={result['final_recommendation']}")

