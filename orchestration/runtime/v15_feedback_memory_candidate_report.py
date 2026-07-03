from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v15_feedback_memory_candidate import sample_feedback_memory_candidate_cases, validate_feedback_memory_candidate_safe


REPORT_MD = Path("reports/runtime_v15g_feedback_memory_candidate_proposal.md")
REPORT_JSON = Path("reports/runtime_v15g_feedback_memory_candidate_proposal.json")


def build_feedback_memory_candidate_report_data() -> dict[str, object]:
    cases = sample_feedback_memory_candidate_cases()
    return {
        "phase": "Runtime V1.5G",
        "title": "Feedback -> Memory Candidate Proposal",
        "status": "review_only_memory_candidate_proposal_no_write_no_recall_no_training",
        "cases": list(cases),
        "case_count": len(cases),
        "all_cases_safe": all(validate_feedback_memory_candidate_safe(case) for case in cases),
        "final_recommendation": "PROCEED_HUMAN_APPROVED_CANONICAL_MEMORY_WRITE_TRIAL_DESIGN",
    }


def write_feedback_memory_candidate_report() -> dict[str, object]:
    data = build_feedback_memory_candidate_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.5G - Feedback -> Memory Candidate Proposal",
        "",
        f"- Status: `{data['status']}`",
        f"- Cases: `{data['case_count']}`",
        f"- All cases safe: `{data['all_cases_safe']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Cases",
        "",
    ]
    for case in data["cases"]:
        lines.append(
            f"- `{case['feedback_signal']['signal_type']}` -> `{case['decision']['outcome']}`; write=`{case['audit_record']['memory_written']}` training=`{case['audit_record']['training_triggered']}`"
        )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_feedback_memory_candidate_report()
    print(f"Runtime V1.5G Feedback Memory Candidate: cases={report['case_count']} safe={report['all_cases_safe']} final={report['final_recommendation']}")
