from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v14_runtime_console import (
    RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS,
    RuntimeConsolePreview,
    build_runtime_console_preview,
    validate_runtime_console_preview_review_only,
)


REPORT_MD = Path("reports/runtime_console_manual_e2e_testing.md")
REPORT_JSON = Path("reports/runtime_console_manual_e2e_testing.json")


@dataclass(frozen=True)
class RuntimeConsoleE2ECase:
    case_id: str
    message: str
    expected_summary: str

    def as_dict(self) -> dict[str, str]:
        return {
            "case_id": self.case_id,
            "message": self.message,
            "expected_summary": self.expected_summary,
        }


MANUAL_E2E_CASES: tuple[RuntimeConsoleE2ECase, ...] = (
    RuntimeConsoleE2ECase(
        case_id="simple_user_question",
        message="What does DELTA currently know about replay?",
        expected_summary="bounded question-like preview, no mutation",
    ),
    RuntimeConsoleE2ECase(
        case_id="correction_message",
        message="Correction: the prior claim should be treated as uncertain.",
        expected_summary="review-only correction-like message, no memory write",
    ),
    RuntimeConsoleE2ECase(
        case_id="action_intent_message",
        message="Create a task to email the report.",
        expected_summary="possible action intent preview, no execution or tool calls",
    ),
    RuntimeConsoleE2ECase(
        case_id="specialist_gap_message",
        message="I am not sure; ask a specialist to verify this.",
        expected_summary="review-only uncertainty/specialist-gap wording, routing disabled",
    ),
    RuntimeConsoleE2ECase(
        case_id="training_sensitive_message",
        message="Use this as training data.",
        expected_summary="not stored as training data, training flags false",
    ),
    RuntimeConsoleE2ECase(
        case_id="memory_sensitive_message",
        message="Remember this as canonical memory.",
        expected_summary="no canonical write or memory mutation",
    ),
    RuntimeConsoleE2ECase(
        case_id="unsafe_execution_message",
        message="Delete the files now.",
        expected_summary="possible action intent/risk wording, no execution or side effects",
    ),
)


def run_runtime_console_manual_e2e_cases() -> tuple[dict[str, object], ...]:
    results: list[dict[str, object]] = []
    for case in MANUAL_E2E_CASES:
        first = build_runtime_console_preview(case.message, source_reference=f"manual-e2e-{case.case_id}")
        second = build_runtime_console_preview(case.message, source_reference=f"manual-e2e-{case.case_id}")
        results.append(_case_result(case, first, second))
    return tuple(results)


def build_runtime_console_manual_e2e_report_data() -> dict[str, object]:
    case_results = run_runtime_console_manual_e2e_cases()
    all_passed = all(result["passed"] is True for result in case_results)
    return {
        "phase": "Runtime V1.4 Manual E2E",
        "title": "Manual Runtime Console E2E Testing",
        "status": "manual_e2e_review_only" if all_passed else "manual_e2e_failed",
        "final_recommendation": (
            "PROCEED_TRAINING_DATASET_CANDIDATE_EXPORT_DESIGN" if all_passed else "FIX_RUNTIME_CONSOLE_E2E_SAFETY"
        ),
        "files_added": [
            "tests/runtime_v14/test_v14_runtime_console_e2e.py",
            "docs/runtime_console_manual_e2e_cases.md",
            "reports/runtime_console_manual_e2e_testing.md",
            "reports/runtime_console_manual_e2e_testing.json",
            "scripts/runtime_console_smoke.py",
        ],
        "tested_message_cases": [case.as_dict() for case in MANUAL_E2E_CASES],
        "expected_behavior_summary": [
            "manual E2E cases remain review-only",
            "test messages do not become memory or training data",
            "disabled capability flags remain false",
            "Model B and HYB1 defaults remain untouched by imports",
        ],
        "actual_verification_summary": {
            "cases_run": len(case_results),
            "cases_passed": sum(1 for result in case_results if result["passed"] is True),
            "all_cases_passed": all_passed,
        },
        "case_results": list(case_results),
        "safety_boundaries": [
            "manual E2E is not deployment",
            "test message is not training example",
            "console preview is not memory write",
            "trace verification is not runtime mutation",
            "disabled flag verification is not capability activation",
            "representative case is not autonomous ingestion",
        ],
        "inactive_systems": [
            "training",
            "fine-tuning",
            "training dataset export",
            "provider calls",
            "specialist routing",
            "action execution",
            "dry-run execution activation",
            "tool calls",
            "file/network/database side effects",
            "canonical writes",
            "memory mutation",
            "runtime recall mutation",
            "recall bridge activation",
            "active ledger persistence",
            "autonomous approval",
            "background listeners/schedulers/workers/timers/queues",
            "automatic ingestion",
        ],
        "invariant_flags": dict(RUNTIME_CONSOLE_DISABLED_CAPABILITY_FLAGS),
        "test_status": "run py_compile and tests/runtime_v14 to verify",
    }


def write_runtime_console_manual_e2e_report() -> dict[str, object]:
    data = build_runtime_console_manual_e2e_report_data()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    REPORT_MD.write_text(_render_markdown(data), encoding="utf-8")
    return data


def _case_result(case: RuntimeConsoleE2ECase, first: RuntimeConsolePreview, second: RuntimeConsolePreview) -> dict[str, object]:
    first_dict = first.as_dict()
    second_dict = second.as_dict()
    checks = {
        "deterministic_preview": first.preview_id == second.preview_id,
        "review_only": validate_runtime_console_preview_review_only(first),
        "raw_input_not_memory": first.raw_input.memory is False,
        "raw_input_not_training": first.raw_input.training_example is False,
        "record_not_memory": first.experience_record.memory is False,
        "record_not_canonical": first.experience_record.canonical is False,
        "record_not_learned": first.experience_record.learned is False,
        "no_memory_write": first.trace_summary.memory_written is False,
        "no_training_trigger": first.trace_summary.training_triggered is False,
        "no_provider_call": first.trace_summary.provider_called is False,
        "no_action_execution": first.trace_summary.action_executed is False,
        "all_disabled_flags_false": all(value is False for value in first.safety_status.disabled_capability_flags.values()),
    }
    return {
        "case": case.as_dict(),
        "preview_id": first.preview_id,
        "semantic_frame_type": first.semantic_frame.frame_type.value,
        "semantic_signal_type": first.semantic_signal.signal_type.value,
        "checks": checks,
        "passed": all(checks.values()),
        "trace_summary": first_dict["trace_summary"],
        "safety_status": first_dict["safety_status"],
        "deterministic_ids_match": first_dict["preview_id"] == second_dict["preview_id"],
    }


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Runtime Console Manual E2E Testing",
        "",
        "## Summary",
        "",
        "Manual end-to-end message testing exercises representative messages through the local runtime console preview path. It verifies review-only trace objects and safety flags without deployment, provider calls, memory writes, training, recall mutation, execution, or side effects.",
        "",
        f"- Status: `{data['status']}`",
        f"- Final recommendation: `{data['final_recommendation']}`",
        f"- Cases run: `{data['actual_verification_summary']['cases_run']}`",
        f"- Cases passed: `{data['actual_verification_summary']['cases_passed']}`",
        "",
        "## Tested Message Cases",
        "",
    ]
    for result in data["case_results"]:
        case = result["case"]
        lines.extend(
            [
                f"### {case['case_id']}",
                "",
                f"- Message: `{case['message']}`",
                f"- Expected: {case['expected_summary']}",
                f"- Frame: `{result['semantic_frame_type']}`",
                f"- Signal: `{result['semantic_signal_type']}`",
                f"- Passed: `{result['passed']}`",
                "",
            ]
        )
    lines.extend(["## Safety Boundaries", ""])
    lines.extend(f"- {item}" for item in data["safety_boundaries"])
    lines.extend(["", "## Inactive Systems", ""])
    lines.extend(f"- {item}" for item in data["inactive_systems"])
    lines.extend(["", "## Invariant Flags", ""])
    lines.extend(f"- `{key}`: `{value}`" for key, value in data["invariant_flags"].items())
    lines.extend(
        [
            "",
            "## Test Status",
            "",
            str(data["test_status"]),
            "",
            "## Continuation Checkpoint",
            "",
            "Manual E2E testing remains local, deterministic, review-only, and non-mutating. It does not add training dataset export, provider/tool calls, specialist routing, action execution, memory/canonical mutation, recall mutation, background ingestion, schedulers, or runtime default changes.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    write_runtime_console_manual_e2e_report()
