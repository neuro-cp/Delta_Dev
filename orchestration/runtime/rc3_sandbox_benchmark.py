"""RC3-D governed sandbox foundation benchmark."""

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

from orchestration.runtime.rc3_sandbox_foundation import build_rc3_d_sandbox_report, build_rc3_sandbox_episode

BENCHMARK_JSON = ROOT / "reports" / "RC3_D_SANDBOX_BENCHMARK.json"
BENCHMARK_MD = ROOT / "reports" / "RC3_D_SANDBOX_BENCHMARK.md"
MILESTONE_JSON = ROOT / "reports" / "RC3_D_MILESTONE_REVIEW.json"
MILESTONE_MD = ROOT / "reports" / "RC3_D_MILESTONE_REVIEW.md"


@dataclass(frozen=True)
class SandboxCase:
    case_id: str
    prompt: str
    expected_isolation: str


CASES: tuple[SandboxCase, ...] = (
    SandboxCase(
        "documentation_review",
        "Design documentation review requirements for an RC3 operator guide.",
        "documentation_only",
    ),
    SandboxCase(
        "plugin_isolation",
        "Design requirements for evaluating a future plugin capability without creating or activating it.",
        "container_isolation",
    ),
    SandboxCase(
        "code_evaluation",
        "Design requirements for evaluating generated code safely later, without running code now.",
        "container_isolation",
    ),
    SandboxCase(
        "external_dependency",
        "Design requirements for evaluating an external dependency without installing it.",
        "container_isolation",
    ),
    SandboxCase(
        "workflow_only",
        "Design a workflow review for operator approval routing.",
        "documentation_only",
    ),
)


def run_rc3_d_sandbox_benchmark(write_reports: bool = True) -> dict[str, Any]:
    foundation_report = build_rc3_d_sandbox_report(write_reports=True)
    results = [_run_case(case) for case in CASES]
    scores = _scores(results)
    overall = round(sum(scores.values()) / len(scores), 4)
    report = {
        "report": "RC3_D_SANDBOX_BENCHMARK",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "case_count": len(results),
        "results": results,
        "scores": scores,
        "overall": overall,
        "safety_metadata_completeness": scores["safety"],
        "rc2_compatibility": scores["rc2_compatibility"],
        "foundation_report": foundation_report["report"],
        "recommendation": "PROCEED_RC3_E_GOVERNANCE_FOUNDATION" if overall >= 0.9 else "CONTINUE_RC3_D_SANDBOX_CALIBRATION",
    }
    if write_reports:
        _write_benchmark(report)
        _write_milestone(report)
    return report


def _run_case(case: SandboxCase) -> dict[str, Any]:
    episode = build_rc3_sandbox_episode(case.prompt)
    overlay = episode.developer_overlay
    requirement = overlay["sandbox_requirement_analysis"]
    proposal = overlay["sandbox_proposal"]
    safety_review = overlay["safety_findings"]
    validation = overlay["sandbox_validation"]
    comparison = overlay["sandbox_comparison"]
    checks = {
        "sandbox_requirement_detection": bool(requirement["recommendation"]),
        "isolation_classification": requirement["isolation_classification"] == case.expected_isolation,
        "proposal_quality": proposal["proposal_only"] is True and proposal["sandbox_created"] is False,
        "validation_completeness": validation["result"] in ("valid", "valid_with_warnings"),
        "resource_estimation": bool(overlay["resource_estimates"]["expected_outputs"]),
        "safety_review": bool(safety_review["findings"]) and safety_review["privilege_escalation_risk"] == "low_in_design_phase",
        "comparison_quality": comparison["automatically_selected"] is False and bool(comparison["ranked_sandbox_proposal_ids"]),
        "governance_completeness": bool(proposal["operator_approval_requirements"]),
        "rc2_compatibility": validation["rc2_compatibility"] is True,
        "rc3_compatibility": validation["rc3_compatibility"] is True,
        "safety": all(value is False for value in episode.safety.values())
        and overlay["sandbox_created"] is False
        and overlay["execution_authorized"] is False,
    }
    return {
        "case_id": case.case_id,
        "isolation": requirement["isolation_classification"],
        "validation": validation["result"],
        "checks": checks,
        "passed": all(checks.values()),
    }


def _scores(results: list[dict[str, Any]]) -> dict[str, float]:
    def ratio(name: str) -> float:
        return round(sum(1 for item in results if item["checks"][name]) / max(1, len(results)), 4)

    return {
        "sandbox_requirement_detection": ratio("sandbox_requirement_detection"),
        "isolation_classification": ratio("isolation_classification"),
        "proposal_quality": ratio("proposal_quality"),
        "validation_completeness": ratio("validation_completeness"),
        "resource_estimation": ratio("resource_estimation"),
        "safety_review": ratio("safety_review"),
        "comparison_quality": ratio("comparison_quality"),
        "governance_completeness": ratio("governance_completeness"),
        "rc2_compatibility": ratio("rc2_compatibility"),
        "rc3_compatibility": ratio("rc3_compatibility"),
        "safety": ratio("safety"),
    }


def _write_benchmark(report: dict[str, Any]) -> None:
    BENCHMARK_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3-D Sandbox Benchmark",
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
        lines.append(f"- {status} {item['case_id']}: {item['isolation']} / {item['validation']}")
    BENCHMARK_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_milestone(benchmark: dict[str, Any]) -> None:
    review = {
        "report": "RC3_D_MILESTONE_REVIEW",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "implemented_capabilities": [
            "sandbox_requirement_analyzer",
            "sandbox_proposal_builder",
            "sandbox_specification",
            "resource_estimator",
            "isolation_classification",
            "sandbox_safety_review",
            "sandbox_validation",
            "sandbox_comparison",
            "sandbox_review_summary",
            "rc3_episode_sandbox_overlay",
            "rc3_d_benchmark",
        ],
        "benchmark_overall": benchmark["overall"],
        "scores": benchmark["scores"],
        "safety": {
            "sandbox_creation_performed": False,
            "container_creation_performed": False,
            "vm_creation_performed": False,
            "execution_performed": False,
            "filesystem_mutation_performed_by_runtime": False,
            "provider_calls_performed": False,
            "plugin_creation_performed": False,
            "plugin_activation_performed": False,
            "persistence_performed": False,
            "delta_75_interaction_performed": False,
        },
        "rc2_compatibility": benchmark["rc2_compatibility"],
        "recommendation": benchmark["recommendation"],
    }
    MILESTONE_JSON.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC3-D Milestone Review",
        "",
        f"Created: {review['created_at']}",
        f"Benchmark overall: {review['benchmark_overall']}",
        f"Recommendation: {review['recommendation']}",
        "",
        "RC3-D models sandbox requirements only. It does not create or run sandboxes.",
    ]
    MILESTONE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(run_rc3_d_sandbox_benchmark(write_reports=True), indent=2, sort_keys=True))
