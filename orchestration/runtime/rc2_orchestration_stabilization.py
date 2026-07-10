"""RC2 orchestration stabilization audit.

This report consolidates routing precedence, arbitration, adversarial routing,
benchmark, and safety findings. It performs no writes outside report files and
does not mutate the substrate.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_adversarial_routing_benchmark import build_adversarial_routing_report
from orchestration.runtime.rc2_cognitive_capability_benchmark import build_benchmark_report
from orchestration.runtime.rc2_cognitive_episode import build_working_memory_episode_report


REPORT_JSON = ROOT / "reports" / "RC2_ORCHESTRATION_STABILIZATION.json"
REPORT_MD = ROOT / "reports" / "RC2_ORCHESTRATION_STABILIZATION.md"


BASELINE = {
    "overall": 0.8019,
    "followup_memory": 0.5417,
    "conversation_quality": 0.6972,
    "contradiction_detection": 0.9722,
    "analogy": 0.8666,
    "cross_domain_synthesis": 0.7667,
    "long_conversation": 0.9437,
    "multi_concept_retrieval": 0.925,
    "missing_evidence": 0.8438,
}


def build_orchestration_stabilization_report(
    *,
    benchmark: dict[str, Any] | None = None,
    adversarial: dict[str, Any] | None = None,
    working_memory: dict[str, Any] | None = None,
    validation_notes: list[str] | None = None,
    write_reports: bool = True,
) -> dict[str, Any]:
    benchmark = benchmark or build_benchmark_report(write_reports=False)
    adversarial = adversarial or build_adversarial_routing_report(write_reports=False)
    working_memory = working_memory or build_working_memory_episode_report(write_reports=False)
    scores = benchmark["category_scores"]
    pathologies = benchmark.get("text_pathology_review") or {}
    report_voice = pathologies.get("report_voice", {}).get("count", 0)
    scaffold = pathologies.get("generic_scaffold", {}).get("count", 0)
    internal_leaks = pathologies.get("internal_leak", {}).get("count", 0)
    safety_passed = bool(benchmark.get("safety_passed")) and adversarial["safety_metadata_completeness"] == 1.0
    gates = {
        "safety": safety_passed,
        "contradiction_at_or_above_0_95": scores.get("contradiction_detection", 0.0) >= 0.95,
        "analogy_not_materially_regressed": scores.get("analogy", 0.0) >= BASELINE["analogy"] - 0.02,
        "cross_domain_not_materially_regressed": scores.get("cross_domain_synthesis", 0.0) >= BASELINE["cross_domain_synthesis"] - 0.02,
        "long_conversation_not_regressed": scores.get("long_conversation", 0.0) >= BASELINE["long_conversation"] - 0.02,
        "route_collision_accuracy": adversarial["route_collision_accuracy"] >= 0.9,
        "orphan_clarification_accuracy": adversarial["orphan_clarification_accuracy"] >= 0.9,
        "metadata_completeness": adversarial["safety_metadata_completeness"] == 1.0,
        "normal_output_internal_leaks_zero": internal_leaks == 0,
        "report_voice_zero": report_voice == 0,
        "generic_scaffold_zero": scaffold == 0,
    }
    stable = all(gates.values())
    report = {
        "report": "RC2_ORCHESTRATION_STABILIZATION",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "architecture_summary": [
            "RC2 is stabilized around route arbitration rather than new cognitive engines.",
            "Working memory resolves references and branches but must yield to contradiction, analogy, and WRS.",
            "Developer Overlay carries arbitration, CognitiveEpisode, and safety metadata; normal chat stays clean.",
        ],
        "modules_changed": [
            "rc2_route_arbitration",
            "rc2_conversational_mode_router",
            "rc2_cognitive_episode",
            "rc2_contradiction_engine",
            "rc2_analogy_engine",
            "rc2_adversarial_routing_benchmark",
        ],
        "route_precedence_document": "docs/RC2_ROUTING_PRECEDENCE.md",
        "collisions_found": [
            "working memory over-intercepted contradiction prompts with pronouns",
            "analogy phrase 'A and B are like C and D' fell through to concept memory",
            "missing-evidence standalone prompts could be misread as orphan follow-ups",
            "comma-prefixed 'Okay, continue...' did not enter working memory",
        ],
        "collisions_repaired": [
            "contradiction checks now win over working-memory follow-ups",
            "analogy extraction now supports plural 'are like' pattern",
            "working memory avoids no-history missing-evidence and analogy prompts",
            "finalizer records route arbitration and fills safety metadata",
        ],
        "benchmark": {
            "overall_score": benchmark["overall_score"],
            "category_scores": scores,
            "baseline": BASELINE,
            "safety_passed": benchmark.get("safety_passed"),
            "recommendation": benchmark.get("recommendation"),
        },
        "adversarial_routing": {
            "case_count": adversarial["case_count"],
            "route_accuracy": adversarial["route_accuracy"],
            "route_collision_accuracy": adversarial["route_collision_accuracy"],
            "pronoun_reference_accuracy": adversarial["pronoun_reference_accuracy"],
            "branch_return_accuracy": adversarial["branch_return_accuracy"],
            "explicit_topic_override_accuracy": adversarial["explicit_topic_override_accuracy"],
            "orphan_clarification_accuracy": adversarial["orphan_clarification_accuracy"],
            "safety_metadata_completeness": adversarial["safety_metadata_completeness"],
            "internal_leak_count": adversarial["internal_leak_count"],
        },
        "working_memory": {
            "cases_tested": working_memory["cases_tested"],
            "followup_resolution_accuracy": working_memory["followup_resolution_accuracy"],
        },
        "output_pathologies": {
            "report_voice_count": report_voice,
            "generic_scaffold_count": scaffold,
            "internal_leak_count": internal_leaks,
        },
        "gates": gates,
        "gates_passed": stable,
        "safety_findings": {
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "canonical_write_performed": False,
            "noncanonical_write_performed": False,
            "graph_write_performed": False,
            "replay_write_performed": False,
            "autonomous_action_performed": False,
            "scheduler_action_performed": False,
        },
        "remaining_risks": [
            "Novel combination remains the weakest benchmark category.",
            "Recall quality still depends on concept substance and ranking.",
            "WRS abstraction/proposition comparison remains the next cognitive refinement target.",
            "Route arbitration is diagnostic; router dispatch still uses existing ordered checks.",
            "Legacy runtime tests still contain expectations from pre-SQLite and pre-CognitiveEpisode behavior.",
        ],
        "validation_notes": validation_notes or [],
        "readiness_recommendation": "PROCEED_RC2_COGNITIVE_REFINEMENT_FREEZE" if stable else "CONTINUE_ADVERSARIAL_REFINEMENT",
    }
    if write_reports:
        _write_reports(report)
    return report


def _write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Orchestration Stabilization",
        "",
        f"Created: {report['created_at']}",
        f"Recommendation: {report['readiness_recommendation']}",
        "",
        "## Architecture Summary",
        "",
    ]
    lines.extend(f"- {item}" for item in report["architecture_summary"])
    lines.extend(["", "## Gates", ""])
    for key, value in report["gates"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Benchmark", ""])
    lines.append(f"- Overall score: {report['benchmark']['overall_score']}")
    for key, value in report["benchmark"]["category_scores"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Adversarial Routing", ""])
    for key, value in report["adversarial_routing"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Collisions Repaired", ""])
    lines.extend(f"- {item}" for item in report["collisions_repaired"])
    lines.extend(["", "## Remaining Risks", ""])
    lines.extend(f"- {item}" for item in report["remaining_risks"])
    if report.get("validation_notes"):
        lines.extend(["", "## Validation Notes", ""])
        lines.extend(f"- {item}" for item in report["validation_notes"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_orchestration_stabilization_report(write_reports=True)
    print(json.dumps({
        "readiness_recommendation": report["readiness_recommendation"],
        "overall_score": report["benchmark"]["overall_score"],
        "route_accuracy": report["adversarial_routing"]["route_accuracy"],
        "route_collision_accuracy": report["adversarial_routing"]["route_collision_accuracy"],
        "safety_metadata_completeness": report["adversarial_routing"]["safety_metadata_completeness"],
        "gates_passed": all(report["gates"].values()),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
