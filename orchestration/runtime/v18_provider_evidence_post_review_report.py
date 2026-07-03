from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v18_provider_evidence_post_review import review_provider_evidence, validate_provider_evidence_post_review_safe


REPORT_MD = Path("reports/runtime_v18g_provider_evidence_post_review_evaluator_cross_check.md")
REPORT_JSON = Path("reports/runtime_v18g_provider_evidence_post_review_evaluator_cross_check.json")


def write_provider_evidence_post_review_report(question: str = "What is a recent fact DELTA cannot know locally?") -> dict[str, object]:
    data = review_provider_evidence(question)
    data["all_safe"] = validate_provider_evidence_post_review_safe(data)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _render_markdown(data: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Runtime V1.8G - Provider Evidence Post-Review / Evaluator Cross-Check",
            "",
            f"- Outcome: `{data['decision']['outcome']}`",
            f"- Risk flags: `{data['audit_record']['risk_flags']}`",
            f"- Evaluator advisory only: `{data['cross_check_review']['advisory_only']}`",
            f"- All safe: `{data['all_safe']}`",
            "",
            "Provider evidence remains evidence-only. Evaluator/local cross-check remains advisory-only. No promotion, memory write, recall mutation, training, or action execution occurred.",
            "",
            f"Final recommendation: `{data['final_recommendation']}`",
            "",
        ]
    )


if __name__ == "__main__":
    result = write_provider_evidence_post_review_report()
    print(f"Runtime V1.8G provider post-review: safe={result['all_safe']} final={result['final_recommendation']}")
