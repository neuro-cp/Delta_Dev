from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v17_provider_assisted_unknown_answer import answer_unknown_with_controlled_provider, validate_unknown_answer_safe


REPORT_MD = Path("reports/runtime_v17c_controlled_provider_assisted_unknown_answer_path.md")
REPORT_JSON = Path("reports/runtime_v17c_controlled_provider_assisted_unknown_answer_path.json")


def write_provider_assisted_unknown_answer_report() -> dict[str, object]:
    known = answer_unknown_with_controlled_provider("What is Model B?")
    unknown = answer_unknown_with_controlled_provider("What is a recent fact DELTA cannot know locally?")
    data = {"phase": "Runtime V1.7C", "known": known, "unknown": unknown, "all_safe": validate_unknown_answer_safe(known) and validate_unknown_answer_safe(unknown), "final_recommendation": "PROCEED_SPECIALIST_SLM_EVIDENCE_ACQUISITION_TRIAL"}
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V1.7C - Controlled Provider-Assisted Unknown Answer Path\n\n"
        f"- All safe: `{data['all_safe']}`\n"
        f"- Unknown decision: `{unknown['decision']['decision']}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n\n"
        "Known local questions stay local. Unknown questions dry-run provider requests by default. Provider responses are evidence packets only, never authority or memory.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    report = write_provider_assisted_unknown_answer_report()
    print(f"Runtime V1.7C unknown answer path: safe={report['all_safe']} final={report['final_recommendation']}")
