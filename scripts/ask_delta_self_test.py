from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v15_first_interaction import build_first_interaction_result  # noqa: E402


SELF_QUESTIONS: tuple[str, ...] = (
    "What is DELTA's current replay and consolidation path?",
    "Can DELTA remember things yet?",
    "Are canonical writes enabled?",
    "Can DELTA call providers?",
    "Can DELTA execute actions?",
    "Can DELTA train itself yet?",
    "What is HYB1?",
    "Is HYB1 active?",
    "What is Model B?",
    "What is the integration gate status?",
    "What is the runtime console purpose?",
    "What is the experience adapter?",
    "What is the semantic adapter?",
    "What is feedback capture?",
    "What is controlled learning?",
    "What is offline evaluation?",
    "What is promotion and rollback?",
    "What is the local knowledge router?",
    "What is currently active?",
    "What remains scaffold-only?",
    "What is still disabled?",
    "What can DELTA not answer yet?",
    "What is the safest next activation gate?",
    "What is needed before memory writes?",
    "What is needed before recall?",
    "What is needed before provider calls?",
)

REPORT_MD = ROOT / "reports" / "runtime_v15f_self_question_test_pack.md"
REPORT_JSON = ROOT / "reports" / "runtime_v15f_self_question_test_pack.json"


def run_self_questions() -> dict[str, object]:
    results = []
    for question in SELF_QUESTIONS:
        data = build_first_interaction_result(question)
        response = data["response_preview"]["response_text"]
        unsupported = "cannot answer that from the local DELTA scaffold yet" in response
        safety = data["safety_status"]
        trace = data["trace"]
        flags = data["invariant_flags"]
        results.append(
            {
                "question": question,
                "response_mode": data["response_preview"]["response_mode"],
                "unsupported": unsupported,
                "trace_id": trace["trace_id"],
                "experience_preview_id": trace["experience_preview_id"],
                "semantic_preview_id": trace["semantic_preview_id"],
                "persisted_to_memory": trace["persisted_to_memory"],
                "persisted_to_canonical_store": trace["persisted_to_canonical_store"],
                "provider_calls_enabled": safety["provider_calls_enabled"],
                "tool_calls_enabled": safety["tool_calls_enabled"],
                "action_execution_enabled": safety["action_execution_enabled"],
                "training_enabled": safety["training_enabled"],
                "canonical_write_enabled": safety["canonical_write_enabled"],
                "runtime_recall_mutation_enabled": safety["runtime_recall_mutation_enabled"],
                "hyb1_default_activation_enabled": safety["hyb1_default_activation_enabled"],
                "model_b_default_changed": flags["model_b_default_changed"],
            }
        )
    unsupported_count = sum(1 for item in results if item["unsupported"])
    data = {
        "phase": "Runtime V1.5F",
        "title": "Self-Question Test Pack",
        "status": "deterministic_self_question_test_no_provider_no_memory_no_training",
        "question_count": len(results),
        "supported_local_answer_count": len(results) - unsupported_count,
        "unsupported_count": unsupported_count,
        "results": results,
        "final_recommendation": "PROCEED_FEEDBACK_TO_MEMORY_CANDIDATE_PROPOSAL",
    }
    return data


def write_self_question_report() -> dict[str, object]:
    data = run_self_questions()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# Runtime V1.5F - Self-Question Test Pack",
        "",
        f"- Status: `{data['status']}`",
        f"- Questions: `{data['question_count']}`",
        f"- Supported local answers: `{data['supported_local_answer_count']}`",
        f"- Unsupported: `{data['unsupported_count']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        "",
        "## Results",
        "",
    ]
    for result in data["results"]:
        lines.append(f"- `{result['question']}` -> `{result['response_mode']}` unsupported=`{result['unsupported']}`")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


def format_self_question_summary(data: dict[str, object]) -> str:
    return "\n".join(
        [
            "Runtime V1.5F Self-Question Test Pack",
            f"questions: {data['question_count']}",
            f"supported_local_answers: {data['supported_local_answer_count']}",
            f"unsupported: {data['unsupported_count']}",
            f"final_recommendation: {data['final_recommendation']}",
        ]
    )


def main() -> int:
    data = write_self_question_report()
    print(format_self_question_summary(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
