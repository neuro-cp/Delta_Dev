from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v17_specialist_evidence_acquisition_trial import run_specialist_evidence_trial, validate_specialist_evidence_trial_safe


REPORT_MD = Path("reports/runtime_v17d_specialist_slm_evidence_acquisition_trial.md")
REPORT_JSON = Path("reports/runtime_v17d_specialist_slm_evidence_acquisition_trial.json")


def write_specialist_evidence_trial_report() -> dict[str, object]:
    known = run_specialist_evidence_trial("What is Model B?")
    unknown = run_specialist_evidence_trial("Analyze this specialized unknown question.", specialist_domain="analysis")
    data = {"phase": "Runtime V1.7D", "known": known, "unknown": unknown, "all_safe": validate_specialist_evidence_trial_safe(known) and validate_specialist_evidence_trial_safe(unknown), "final_recommendation": "PROCEED_PROVIDER_EVIDENCE_REVIEW_UI_OR_LIMITED_GENERAL_RECALL_TRIAL"}
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V1.7D - Specialist / SLM Evidence Acquisition Trial\n\n"
        f"- All safe: `{data['all_safe']}`\n"
        f"- Unknown decision: `{unknown['decision']['decision']}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n\n"
        "Specialist results are evidence-only and not authority, memory, promotion, training, or action execution.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    report = write_specialist_evidence_trial_report()
    print(f"Runtime V1.7D specialist evidence trial: safe={report['all_safe']} final={report['final_recommendation']}")
