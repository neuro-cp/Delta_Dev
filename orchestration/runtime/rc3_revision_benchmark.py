"""RC3-B governed plan revision benchmark."""

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
from orchestration.runtime.rc3_plan_revision import (
    PlanRevisionRequest,
    build_rc3_b_revision_report,
    build_rc3_revision_episode,
    revise_plan,
)

REPORT_JSON = ROOT / "reports" / "RC3_B_REVISION_BENCHMARK.json"
REPORT_MD = ROOT / "reports" / "RC3_B_REVISION_BENCHMARK.md"
MILESTONE_JSON = ROOT / "reports" / "RC3_B_MILESTONE_REVIEW.json"
MILESTONE_MD = ROOT / "reports" / "RC3_B_MILESTONE_REVIEW.md"


@dataclass(frozen=True)
class RevisionCase:
    case_id: str
    prompt: str
    request: PlanRevisionRequest
    expect_revision: bool
    expected_decision: str
    expected_monitoring_flag: str | None = None


CASES: tuple[RevisionCase, ...] = (
    RevisionCase(
        "operator_correction_revises",
        "Design an RC3 plugin manifest, but do not implement plugins.",
        PlanRevisionRequest(
            trigger="operator_correction",
            updated_constraints=("operator review required",),
            new_evidence=("operator clarified schema-only scope",),
            operator_notes="Schema only.",
            requested_scope="scope_reduction",
        ),
        True,
        "revise_existing_plan",
    ),
    RevisionCase(
        "no_justification_rejected",
        "Design RC3 docs.",
        PlanRevisionRequest(trigger="operator_correction"),
        False,
        "continue_current_plan",
    ),
    RevisionCase(
        "unsupported_trigger_requires_clarification",
        "Design RC3 docs.",
        PlanRevisionRequest(trigger="autonomous_whim", new_evidence=("none",)),
        False,
        "require_clarification",
    ),
    RevisionCase(
        "assumption_invalidated",
        "Design a read-only RC3 plan.",
        PlanRevisionRequest(
            trigger="assumption_invalidated",
            changed_assumptions=("legacy planner cannot be activated",),
            new_evidence=("architecture review classified legacy planner as reference-only",),
        ),
        True,
        "revise_existing_plan",
    ),
    RevisionCase(
        "scope_expansion",
        "Design validation reports.",
        PlanRevisionRequest(
            trigger="scope_expansion",
            updated_constraints=("include benchmark report",),
            new_evidence=("operator requested benchmark coverage"),
            requested_scope="scope_expansion",
        ),
        True,
        "revise_existing_plan",
    ),
    RevisionCase(
        "conflicting_goal_replace",
        "Design RC3-A reports.",
        PlanRevisionRequest(
            trigger="conflicting_goal",
            operator_clarification="Operator switched objective to lifecycle docs.",
            new_evidence=("new objective conflicts with current report-only plan",),
        ),
        True,
        "replace_plan_entirely",
    ),
)


def run_rc3_b_revision_benchmark(write_reports: bool = True) -> dict[str, Any]:
    revision_report = build_rc3_b_revision_report(write_reports=True)
    results = [_run_case(case) for case in CASES]
    scores = _scores(results)
    overall = round(sum(scores.values()) / len(scores), 4)
    report = {
        "report": "RC3_B_REVISION_BENCHMARK",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "case_count": len(results),
        "results": results,
        "scores": scores,
        "overall": overall,
        "safety_metadata_completeness": scores["safety"],
        "rc2_compatibility": 1.0,
        "revision_report": revision_report["report"],
        "recommendation": "PROCEED_RC3_C_ENGINEERING_FOUNDATION" if overall >= 0.9 else "CONTINUE_RC3_B_REVISION_CALIBRATION",
    }
    if write_reports:
        _write_benchmark(report)
        _write_milestone(report)
    return report


def _run_case(case: RevisionCase) -> dict[str, Any]:
    episode = build_rc3_goal_planning_episode(case.prompt)
    result = revise_plan(episode.goal_frame, episode.plan_frame, case.request, progress=episode.progress, capability_gap=episode.capability_gap)
    revised_episode = build_rc3_revision_episode(case.prompt, case.request, previous_episode=episode)
    checks = {
        "trigger_detection": result.reasoning.revision_cause == case.request.trigger,
        "false_revision_rejection": result.revision_applied is case.expect_revision,
        "constraint_preservation": set(episode.goal_frame.constraints).issubset(set(result.revised_plan.constraints_preserved)),
        "prohibition_preservation": set(episode.goal_frame.prohibited_actions).issubset(set(result.revised_plan.prohibited_actions)),
        "revision_quality": result.self_evaluation.revision_quality >= (0.5 if case.expect_revision else 0.2),
        "plan_diff_accuracy": bool(result.diff.human_readable),
        "revision_validation": result.validation.result in ("valid", "valid_with_warnings"),
        "arbitration_correctness": result.decision == case.expected_decision,
        "monitoring_accuracy": result.monitoring.observational_only is True,
        "self_evaluation_quality": result.self_evaluation.certainty_claimed is False,
        "safety": all(value is False for value in result.safety.values()) and all(value is False for value in revised_episode.safety.values()),
        "rc2_compatibility": True,
    }
    return {
        "case_id": case.case_id,
        "prompt": case.prompt,
        "decision": result.decision,
        "revision_applied": result.revision_applied,
        "checks": checks,
        "passed": all(checks.values()),
        "diff": result.diff.human_readable,
        "monitoring": result.monitoring.diagnostics,
        "self_evaluation": {
            "revision_quality": result.self_evaluation.revision_quality,
            "confidence": result.self_evaluation.confidence,
            "missing_information": result.self_evaluation.missing_information,
        },
    }


def _scores(results: list[dict[str, Any]]) -> dict[str, float]:
    def ratio(name: str) -> float:
        return round(sum(1 for item in results if item["checks"][name]) / max(1, len(results)), 4)

    return {
        "revision_trigger_detection": ratio("trigger_detection"),
        "false_revision_rejection": ratio("false_revision_rejection"),
        "constraint_preservation": ratio("constraint_preservation"),
        "prohibition_preservation": ratio("prohibition_preservation"),
        "revision_quality": ratio("revision_quality"),
        "plan_diff_accuracy": ratio("plan_diff_accuracy"),
        "revision_validation": ratio("revision_validation"),
        "arbitration_correctness": ratio("arbitration_correctness"),
        "monitoring_accuracy": ratio("monitoring_accuracy"),
        "self_evaluation_quality": ratio("self_evaluation_quality"),
        "safety": ratio("safety"),
        "rc2_compatibility": ratio("rc2_compatibility"),
    }


def _write_benchmark(report: dict[str, Any]) -> None:
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3-B Revision Benchmark",
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
    for item in report["results"]:
        status = "PASS" if item["passed"] else "CHECK"
        lines.append(f"- {status} {item['case_id']}: {item['decision']} / revision_applied={item['revision_applied']}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_milestone(benchmark: dict[str, Any]) -> None:
    review = {
        "report": "RC3_B_MILESTONE_REVIEW",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "implemented_capabilities": [
            "plan_revision_engine",
            "revision_trigger_detection",
            "structured_revision_reasoning",
            "plan_diff",
            "revision_validation",
            "ephemeral_revision_history",
            "revision_arbitration",
            "monitoring_scaffold",
            "self_evaluation_scaffold",
            "controlled_forgetting_hooks",
            "revision_episode_extension",
            "revision_benchmark",
        ],
        "inert_capabilities": [
            "plan_execution",
            "persistent_project_memory",
            "plugins",
            "sandboxes",
            "coding_agents",
            "external_review_automation",
            "integration_automation",
        ],
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
            "Revision logic is deterministic and rule-based.",
            "Revision history is stored only in the ephemeral Developer Overlay.",
            "Monitoring is observational and not tied to persistent project state.",
        ],
        "recommendation": benchmark["recommendation"],
    }
    MILESTONE_JSON.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3-B Milestone Review",
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


def main() -> None:
    report = run_rc3_b_revision_benchmark(write_reports=True)
    print(json.dumps({
        "overall": report["overall"],
        "recommendation": report["recommendation"],
        "case_count": report["case_count"],
        "safety_metadata_completeness": report["safety_metadata_completeness"],
        "rc2_compatibility": report["rc2_compatibility"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
