from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v22_evaluator_assisted_memory_candidate_review import (
    EvaluatorCandidateReviewInput,
    review_memory_candidate_with_evaluator,
    validate_evaluator_candidate_review_safe,
)


REPORT_MD = Path("reports/runtime_v22d_evaluator_assisted_memory_candidate_review.md")
REPORT_JSON = Path("reports/runtime_v22d_evaluator_assisted_memory_candidate_review.json")


def write_evaluator_candidate_review_report() -> dict[str, object]:
    cases = [
        review_memory_candidate_with_evaluator(EvaluatorCandidateReviewInput("candidate-good", "Reviewed candidate.", ("source",))),
        review_memory_candidate_with_evaluator(EvaluatorCandidateReviewInput("candidate-ambiguous", "Maybe save this.", ("source",), ambiguity_flag=True)),
    ]
    data = {
        "phase": "Runtime V2.2D",
        "cases": cases,
        "all_safe": all(validate_evaluator_candidate_review_safe(case) for case in cases),
        "final_recommendation": "PROCEED_HYB1_OPT_IN_SHADOW_TRIAL_DESIGN",
    }
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return "\n".join((
        "# Runtime V2.2D - Evaluator-Assisted Memory Candidate Review",
        "",
        "Evaluator review is advisory only. It cannot approve, write, delete, mutate recall, or train.",
        "",
        f"All safe: `{data['all_safe']}`",
        f"Final recommendation: `{data['final_recommendation']}`",
        "",
    ))


if __name__ == "__main__":
    result = write_evaluator_candidate_review_report()
    print(f"Runtime V2.2D evaluator review: safe={result['all_safe']} final={result['final_recommendation']}")
