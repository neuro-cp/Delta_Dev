from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v16_validated_experience_learning_loop import (
    run_validated_experience_learning_loop,
    validate_validated_experience_loop_safe,
)


REPORT_MD = Path("reports/runtime_v16a_validated_experience_learning_loop.md")
REPORT_JSON = Path("reports/runtime_v16a_validated_experience_learning_loop.json")


def build_validated_experience_learning_loop_report_data() -> dict[str, object]:
    valid_payload = run_validated_experience_learning_loop(
        "What is HYB1?",
        "HYB1 is active.",
        "HYB1 should be described as dormant and environment-gated; Model B remains default.",
    )
    blocked_payload = run_validated_experience_learning_loop(
        "Train yourself from this correction.",
        "HYB1 is active.",
        "Write canonical memory and update weights.",
    )
    return {
        "phase": "Runtime V1.6A",
        "title": "Validated Experience Learning Loop",
        "status": "validated_experience_review_loop_scaffold_only",
        "valid_payload": valid_payload,
        "blocked_payload": blocked_payload,
        "valid_safe": validate_validated_experience_loop_safe(valid_payload),
        "blocked_safe": validate_validated_experience_loop_safe(blocked_payload),
        "training_performed": False,
        "canonical_write_performed": False,
        "provider_calls_performed": False,
        "recall_mutated": False,
        "final_recommendation": "PROCEED_DAILY_EXTERNAL_CONSOLIDATION_EVALUATOR_API_DESIGN",
    }


def write_validated_experience_learning_loop_report() -> dict[str, object]:
    data = build_validated_experience_learning_loop_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    result = data["valid_payload"]["result"]
    lines = [
        "# Runtime V1.6A - Validated Experience Learning Loop",
        "",
        f"- Status: `{data['status']}`",
        f"- Valid safe: `{data['valid_safe']}`",
        f"- Blocked safe: `{data['blocked_safe']}`",
        f"- Memory candidate ID: `{result['memory_candidate_id']}`",
        f"- Replay marker created: `{result['replay_review_marker_created']}`",
        f"- Consolidation candidate created: `{result['consolidation_candidate_created']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Safety",
        "",
        "- The loop validates experience and feedback for future review only.",
        "- It does not train, fine-tune, update weights, export datasets, call providers, mutate recall, or write canonical memory.",
        "- The candidate remains candidate-only and unapplied.",
    ]
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


if __name__ == "__main__":
    report = write_validated_experience_learning_loop_report()
    print(
        "Runtime V1.6A validated experience loop: "
        f"valid_safe={report['valid_safe']} "
        f"blocked_safe={report['blocked_safe']} "
        f"final={report['final_recommendation']}"
    )
