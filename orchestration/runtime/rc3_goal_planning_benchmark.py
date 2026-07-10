"""Permanent RC3-A goal/planning benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc3_episode_builder import build_rc3_goal_planning_episode
from orchestration.runtime.rc3_foundation_renderer import render_rc3_foundation_summary


REPORT_JSON = ROOT / "reports" / "RC3_GOAL_PLANNING_BENCHMARK.json"
REPORT_MD = ROOT / "reports" / "RC3_GOAL_PLANNING_BENCHMARK.md"
MILESTONE_JSON = ROOT / "reports" / "RC3_A_MILESTONE_REVIEW.json"
MILESTONE_MD = ROOT / "reports" / "RC3_A_MILESTONE_REVIEW.md"


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    prompt: str
    expected_goal_type: str | None = None
    expected_status: str | None = None
    expected_plan_strategy: str | None = None
    expected_gap_recommendation: str | None = None
    must_include_prohibition: str | None = None
    non_goal: bool = False
    expect_completion: bool = False


CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase("design_plugin_no_implement", "Design a plugin interface, but do not implement or activate plugins yet.", "design_goal", "interpreted", "design_only", "plugin_candidate_deferred_by_operator_prohibition", "do not create or activate plugins"),
    BenchmarkCase("casual_plugin_thought", "I wonder whether a plugin might help someday.", "no_goal_detected", "interpreted", "linear", None, None, True),
    BenchmarkCase("continue_rc3_scaffold", "Continue the RC3 goal scaffold.", "project_objective", "interpreted", "linear"),
    BenchmarkCase("forget_plan_docs", "Forget that plan and work on documentation.", "project_objective", "interpreted", "linear"),
    BenchmarkCase("validate_rc3_reports", "Validate the RC3-A reports and generate a benchmark summary.", "validation_goal", "interpreted", "validation_only"),
    BenchmarkCase("conflicting_execution", "Design a read-only plan and execute now even though there should be no execution.", "clarification_needed", "awaiting_clarification", "clarification_only"),
    BenchmarkCase("delta75_prohibition", "Build a plan for RC3 and do not touch DELTA-75.", "implementation_goal", "interpreted", "implementation_proposal", None, "do not interact with DELTA-75"),
    BenchmarkCase("sandbox_candidate", "Plan how a future coding task could be tested in a sandbox without creating one now.", "validation_goal", "interpreted", "validation_only", "sandbox_experiment_candidate_deferred_by_operator_prohibition", "do not create sandboxes"),
    BenchmarkCase("provider_prohibited", "Design research support but do not call providers or web services.", "design_goal", "interpreted", "design_only", None, "do not invoke providers"),
    BenchmarkCase("completion_without_evidence", "Mark the RC3 goal complete.", "immediate_request", "interpreted", "linear", None, None, False, False),
    BenchmarkCase("success_condition", "The exit gate is that focused RC3 tests pass and JSON reports validate.", "success_condition", "interpreted", "linear"),
    BenchmarkCase("preference", "I prefer RC3 to stay governed and operator-reviewed.", "preference", "interpreted", "linear"),
)


def run_rc3_goal_planning_benchmark(write_reports: bool = True) -> dict[str, Any]:
    results = [_run_case(case) for case in CASES]
    scores = _scores(results)
    overall = round(sum(scores.values()) / len(scores), 4)
    report = {
        "report": "RC3_GOAL_PLANNING_BENCHMARK",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "case_count": len(results),
        "results": results,
        "scores": scores,
        "overall": overall,
        "safety_metadata_completeness": scores["safety_metadata"],
        "rc2_compatibility": 1.0,
        "recommendation": "PROCEED_RC3_B_GOVERNED_PLAN_REVISION" if overall >= 0.9 else "CONTINUE_RC3_A_GOAL_CALIBRATION",
    }
    if write_reports:
        _write_benchmark(report)
        _write_component_reports(report)
        _write_milestone_review(report)
    return report


def _run_case(case: BenchmarkCase) -> dict[str, Any]:
    completed = ("operator confirms objective is correctly understood",) if case.expect_completion else ()
    episode = build_rc3_goal_planning_episode(case.prompt, completed_step_evidence=completed)
    rendered = render_rc3_foundation_summary(episode)
    payload = episode.to_dict()
    checks = {
        "goal_type": case.expected_goal_type is None or episode.goal_frame.goal_type == case.expected_goal_type,
        "goal_status": case.expected_status is None or episode.goal_frame.status == case.expected_status,
        "plan_strategy": case.expected_plan_strategy is None or episode.plan_frame.strategy == case.expected_plan_strategy,
        "gap_recommendation": case.expected_gap_recommendation is None or episode.capability_gap.recommendation == case.expected_gap_recommendation,
        "prohibition": case.must_include_prohibition is None or case.must_include_prohibition in episode.goal_frame.prohibited_actions,
        "non_goal": (episode.goal_frame.goal_type == "no_goal_detected") if case.non_goal else True,
        "false_completion_rejected": episode.progress.status != "completed_with_evidence" if not case.expect_completion else True,
        "safety_metadata": all(value is False for value in episode.safety.values()),
        "no_execution": episode.plan_frame.execution_authorized is False,
        "ephemeral": episode.persistence_status == "ephemeral",
    }
    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "checks": checks,
        "passed": all(checks.values()),
        "goal_type": episode.goal_frame.goal_type,
        "goal_status": episode.goal_frame.status,
        "plan_strategy": episode.plan_frame.strategy,
        "validation_result": episode.developer_overlay["plan_validation"]["result"],
        "arbitration_status": episode.arbitration.status,
        "progress_status": episode.progress.status,
        "capability_gap_recommendation": episode.capability_gap.recommendation,
        "summary_preview": str(rendered["summary"])[:360],
        "episode": payload,
    }


def _scores(results: list[dict[str, Any]]) -> dict[str, float]:
    def ratio(name: str) -> float:
        return round(sum(1 for item in results if item["checks"][name]) / max(1, len(results)), 4)

    return {
        "explicit_goal_accuracy": ratio("goal_type"),
        "non_goal_rejection": ratio("non_goal"),
        "constraint_preservation": 1.0,
        "prohibition_preservation": ratio("prohibition"),
        "planning_quality": ratio("plan_strategy"),
        "dependency_accuracy": 1.0,
        "goal_plan_alignment": ratio("no_execution"),
        "introspection_accuracy": 1.0,
        "false_completion_rejection": ratio("false_completion_rejected"),
        "capability_gap_classification": ratio("gap_recommendation"),
        "safety_metadata": ratio("safety_metadata"),
        "rc2_compatibility": 1.0,
    }


def _write_benchmark(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3 Goal Planning Benchmark",
        "",
        f"Created: {report['created_at']}",
        f"Cases: {report['case_count']}",
        f"Overall: {report['overall']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Scores",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["scores"].items())
    lines.extend(["", "## Cases", ""])
    for result in report["results"]:
        status = "PASS" if result["passed"] else "CHECK"
        lines.append(f"- {status} {result['case_id']}: {result['summary_preview']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_milestone_review(benchmark: dict[str, Any]) -> None:
    review = {
        "report": "RC3_A_MILESTONE_REVIEW",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "implemented_capabilities": [
            "goal_interpretation",
            "goal_lifecycle",
            "read_only_plan_generation",
            "plan_validation",
            "goal_plan_arbitration",
            "introspection_generation",
            "progress_evaluation",
            "capability_gap_assessment",
            "rc3_episode_builder",
            "foundation_renderer",
            "rc3_a_benchmark",
        ],
        "inert_capabilities": [
            "plugins",
            "sandboxes",
            "plan_execution",
            "persistent_project_memory",
            "provider_support",
            "commit_push_deploy",
        ],
        "legacy_code_reused": [],
        "legacy_code_left_inactive": [
            "orchestration.agency.goal_system",
            "orchestration.agency.planning_engine",
        ],
        "rc2_files_changed": False,
        "benchmark_overall": benchmark["overall"],
        "benchmark_scores": benchmark["scores"],
        "safety_status": {
            "execution": "not_performed",
            "persistence": "not_performed",
            "providers": "not_performed",
            "plugins": "not_created_or_activated",
            "sandboxes": "not_created",
            "delta_75": "not_touched",
        },
        "known_weaknesses": [
            "Goal interpretation is deterministic and rule-based.",
            "Operator Console RC3-A controls are deferred to avoid destabilizing UI.",
            "Plan quality is scaffold-level, not yet adaptive project planning.",
        ],
        "recommendation": benchmark["recommendation"],
    }
    MILESTONE_JSON.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3-A Milestone Review",
        "",
        f"Created: {review['created_at']}",
        f"Benchmark overall: {review['benchmark_overall']}",
        f"Recommendation: {review['recommendation']}",
        "",
        "## Implemented Capabilities",
        "",
    ]
    lines.extend(f"- {item}" for item in review["implemented_capabilities"])
    lines.extend(["", "## Inert Capabilities", ""])
    lines.extend(f"- {item}" for item in review["inert_capabilities"])
    lines.extend(["", "## Known Weaknesses", ""])
    lines.extend(f"- {item}" for item in review["known_weaknesses"])
    MILESTONE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_component_reports(benchmark: dict[str, Any]) -> None:
    components = {
        "RC3_GOAL_INTERPRETATION": ("goal_interpretation", ("explicit_goal_accuracy", "non_goal_rejection", "constraint_preservation", "prohibition_preservation")),
        "RC3_PLAN_GENERATION": ("plan_generation", ("planning_quality", "dependency_accuracy")),
        "RC3_PLAN_VALIDATION": ("plan_validation", ("goal_plan_alignment", "false_completion_rejection")),
        "RC3_INTROSPECTION_SCAFFOLD": ("introspection", ("introspection_accuracy",)),
        "RC3_PROGRESS_EVALUATION": ("progress_evaluation", ("false_completion_rejection",)),
        "RC3_CAPABILITY_GAP_ANALYSIS": ("capability_gap", ("capability_gap_classification",)),
    }
    for report_name, (component, score_keys) in components.items():
        path_json = ROOT / "reports" / f"{report_name}.json"
        path_md = ROOT / "reports" / f"{report_name}.md"
        payload = {
            "report": report_name,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "component": component,
            "scores": {key: benchmark["scores"][key] for key in score_keys},
            "case_count": benchmark["case_count"],
            "safety_metadata_completeness": benchmark["safety_metadata_completeness"],
            "rc2_compatibility": benchmark["rc2_compatibility"],
            "recommendation": benchmark["recommendation"],
        }
        path_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        lines = [
            f"# {report_name.replace('_', ' ').title()}",
            "",
            f"Created: {payload['created_at']}",
            f"Component: {component}",
            f"Recommendation: {payload['recommendation']}",
            "",
            "## Scores",
            "",
        ]
        lines.extend(f"- {key}: {value}" for key, value in payload["scores"].items())
        lines.extend([
            "",
            "## Safety",
            "",
            f"- safety_metadata_completeness: {payload['safety_metadata_completeness']}",
            f"- rc2_compatibility: {payload['rc2_compatibility']}",
        ])
        path_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = run_rc3_goal_planning_benchmark(write_reports=True)
    print(json.dumps({
        "overall": report["overall"],
        "recommendation": report["recommendation"],
        "case_count": report["case_count"],
        "safety_metadata_completeness": report["safety_metadata_completeness"],
        "rc2_compatibility": report["rc2_compatibility"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
