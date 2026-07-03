from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_memory_candidate_review_loop import (
    build_memory_candidate_review_request,
    defer_memory_candidate,
    mark_memory_candidate_ready_for_explicit_approval,
    propose_memory_candidate_edit,
    reject_memory_candidate,
    request_more_evidence_for_memory_candidate,
    validate_memory_candidate_review_safe,
)


REPORT_MD = Path("reports/runtime_v16i_memory_candidate_edit_reject_defer_loop.md")
REPORT_JSON = Path("reports/runtime_v16i_memory_candidate_edit_reject_defer_loop.json")


def write_memory_candidate_review_loop_report() -> dict[str, object]:
    request = build_memory_candidate_review_request("memory-candidate-60ee56fb323e53de", "No memory candidate should be written without review.")
    cases = {
        "edit": propose_memory_candidate_edit(request, "Memory candidates from ambiguous feedback require human review before any canonical write."),
        "reject": reject_memory_candidate(request),
        "defer": defer_memory_candidate(request),
        "more_evidence": request_more_evidence_for_memory_candidate(request),
        "ready": mark_memory_candidate_ready_for_explicit_approval(request),
    }
    data = {
        "phase": "Runtime V1.6I",
        "title": "Memory Candidate Edit / Reject / Defer Loop",
        "cases": cases,
        "all_safe": all(validate_memory_candidate_review_safe(payload) for payload in cases.values()),
        "final_recommendation": "PROCEED_CANONICAL_MEMORY_ROLLBACK_TRIAL",
    }
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(
        "# Runtime V1.6I - Memory Candidate Edit / Reject / Defer Loop\n\n"
        f"- All safe: `{data['all_safe']}`\n"
        f"- Cases: `{len(cases)}`\n"
        f"- Final recommendation: `{data['final_recommendation']}`\n\n"
        "All decisions are review-only. No canonical write, memory write, recall mutation, provider call, training, action execution, HYB1 promotion, or Model B change occurs.\n",
        encoding="utf-8",
    )
    return data


if __name__ == "__main__":
    report = write_memory_candidate_review_loop_report()
    print(f"Runtime V1.6I memory candidate review loop: safe={report['all_safe']} cases={len(report['cases'])} final={report['final_recommendation']}")
