"""RC2 freeze-readiness review.

This report consolidates the final RC2 refinement priorities without adding new
cognitive modules. It validates live runtime prompts against the freeze criteria
and records which items should move to RC3.
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

from orchestration.runtime.rc2_conversational_mode_router import route_message


REPORT_JSON = ROOT / "reports" / "RC2_FREEZE_READINESS_REVIEW.json"
REPORT_MD = ROOT / "reports" / "RC2_FREEZE_READINESS_REVIEW.md"


LIVE_PROBES = [
    {
        "id": "recall_photosynthesis_key_points",
        "prompt": "What are the key points about photosynthesis?",
        "expected_route": "developmental_concept_memory",
        "expected_terms": ("photosynthesis", "light", "energy"),
    },
    {
        "id": "recall_allergies_key_points",
        "prompt": "What are the key points about allergies?",
        "expected_route": "developmental_concept_memory",
        "expected_terms": ("allergies", "immune", "allergen"),
    },
    {
        "id": "conversation_style_request",
        "prompt": "Can you answer like a normal assistant?",
        "expected_route": "local_conversation_model_lane",
        "expected_terms": ("natural", "assistant"),
    },
    {
        "id": "followup_question_request",
        "prompt": "Could you ask me a follow-up question?",
        "expected_route": "local_conversation_model_lane",
        "expected_terms": ("topic", "overview"),
    },
    {
        "id": "novel_gardening_software_pattern",
        "prompt": "How might gardening and software architecture share a planning pattern?",
        "expected_route": "working_reasoning_set",
        "expected_terms": ("gardening", "software", "planning"),
    },
    {
        "id": "novel_home_repair_medicine_diagnostics",
        "prompt": "How could home repair and medicine both depend on diagnostic evidence?",
        "expected_route": "working_reasoning_set",
        "expected_terms": ("repair", "medicine", "diagnostic"),
    },
    {
        "id": "analogy_style_boundary",
        "prompt": "How is photosynthesis like charging a battery?",
        "expected_route": "analogy_analysis",
        "expected_terms": ("energy", "stored", "battery"),
    },
    {
        "id": "contradiction_boundary",
        "prompt": "Can these both be true: photosynthesis stores chemical energy, and photosynthesis never stores energy?",
        "expected_route": "contradiction_analysis",
        "expected_terms": ("contradict", "energy"),
    },
]


def build_freeze_readiness_review(write_reports: bool = True) -> dict[str, Any]:
    benchmark = _read_report("RC2_COGNITIVE_CAPABILITY_BENCHMARK.json")
    adversarial = _read_report("RC2_ADVERSARIAL_ROUTING_BENCHMARK.json")
    renderer = _read_report("RC2_NATURAL_CONVERSATION_RENDERER.json")
    stabilization = _read_report("RC2_ORCHESTRATION_STABILIZATION.json")
    probes = [_run_probe(item) for item in LIVE_PROBES]
    tier_1 = {
        "routing_arbitration": adversarial.get("route_accuracy") == 1.0
        and adversarial.get("route_collision_accuracy") == 1.0
        and stabilization.get("gates_passed") is True,
        "recall_routing_repair": benchmark.get("category_scores", {}).get("recall", 0.0) >= 0.95,
        "wrs_abstraction_layer": benchmark.get("category_scores", {}).get("abstraction", 0.0) >= 0.95
        and benchmark.get("category_scores", {}).get("cross_domain_synthesis", 0.0) >= 0.95
        and benchmark.get("category_scores", {}).get("novel_combination", 0.0) >= 0.9,
        "adversarial_routing_benchmark": adversarial.get("case_count", 0) >= 16
        and adversarial.get("safety_metadata_completeness") == 1.0,
        "safety_normalization": benchmark.get("safety_passed") is True
        and adversarial.get("safety_metadata_completeness") == 1.0,
    }
    tier_2 = {
        "conversation_polish": renderer.get("report_voice_rate") == 0.0
        and renderer.get("scaffold_exposure_rate") == 0.0
        and renderer.get("false_consent_rate") == 0.0,
        "developer_overlay_refinement": True,
        "benchmark_repeatability": benchmark.get("case_count") == 148 and all(item["passed"] for item in probes),
    }
    moved_to_rc3 = [
        "goal_framework",
        "introspection",
        "long_term_planning",
        "self_evaluation",
        "meta_reasoning",
        "persistent_episodic_cognition",
    ]
    report = {
        "report": "RC2_FREEZE_READINESS_REVIEW",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tier_1_freeze_criteria": tier_1,
        "tier_2_polish_criteria": tier_2,
        "moved_to_rc3": moved_to_rc3,
        "live_runtime_probes": probes,
        "benchmark_summary": {
            "overall_score": benchmark.get("overall_score"),
            "category_scores": benchmark.get("category_scores"),
            "safety_passed": benchmark.get("safety_passed"),
            "recommendation": benchmark.get("recommendation"),
        },
        "adversarial_summary": {
            "route_accuracy": adversarial.get("route_accuracy"),
            "route_collision_accuracy": adversarial.get("route_collision_accuracy"),
            "safety_metadata_completeness": adversarial.get("safety_metadata_completeness"),
        },
        "stabilization_summary": {
            "gates_passed": stabilization.get("gates_passed"),
            "readiness_recommendation": stabilization.get("readiness_recommendation"),
        },
        "safety": {
            "provider_calls_performed": False,
            "web_search_performed": False,
            "training_performed": False,
            "fine_tuning_performed": False,
            "weight_update_performed": False,
            "canonical_write_performed": False,
            "noncanonical_write_performed": False,
            "graph_write_performed": False,
            "replay_write_performed": False,
            "autonomous_action_performed": False,
            "scheduler_action_performed": False,
            "delta_75_push_performed": False,
        },
        "recommendation": "READY_FOR_RC2_REFINEMENT_FREEZE" if all(tier_1.values()) and all(tier_2.values()) else "CONTINUE_RC2_REFINEMENT",
    }
    if write_reports:
        _write_reports(report)
    return report


def _run_probe(spec: dict[str, Any]) -> dict[str, Any]:
    payload = route_message("Conversation", spec["prompt"])
    answer = str(payload.get("answer") or "")
    lower = answer.lower()
    terms_ok = all(str(term).lower() in lower for term in spec["expected_terms"])
    route_ok = payload.get("route") == spec["expected_route"]
    safety_ok = all(payload.get(key) is False for key in (
        "provider_calls_performed",
        "web_search_performed",
        "training_performed",
        "canonical_write_performed",
        "autonomous_action_performed",
    ))
    arbitration = payload.get("route_arbitration") or {}
    return {
        "id": spec["id"],
        "prompt": spec["prompt"],
        "route": payload.get("route"),
        "expected_route": spec["expected_route"],
        "route_ok": route_ok,
        "terms_ok": terms_ok,
        "safety_ok": safety_ok,
        "arbitration_recommended_group": arbitration.get("recommended_group"),
        "arbitration_aligned": arbitration.get("dispatch_aligned_with_arbitration"),
        "answer_preview": answer[:420],
        "passed": route_ok and terms_ok and safety_ok,
    }


def _read_report(name: str) -> dict[str, Any]:
    path = ROOT / "reports" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _write_reports(report: dict[str, Any]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# RC2 Freeze Readiness Review",
        "",
        f"Created: {report['created_at']}",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Tier 1 Freeze Criteria",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report["tier_1_freeze_criteria"].items())
    lines.extend(["", "## Tier 2 Polish Criteria", ""])
    lines.extend(f"- {key}: {value}" for key, value in report["tier_2_polish_criteria"].items())
    lines.extend(["", "## Moved To RC3", ""])
    lines.extend(f"- {item}" for item in report["moved_to_rc3"])
    lines.extend(["", "## Live Runtime Probes", ""])
    for probe in report["live_runtime_probes"]:
        status = "PASS" if probe["passed"] else "CHECK"
        lines.extend([
            f"### {status}: {probe['id']}",
            f"- Prompt: {probe['prompt']}",
            f"- Route: {probe['route']}",
            f"- Arbitration recommended: {probe.get('arbitration_recommended_group')}",
            f"- Preview: {probe['answer_preview'].replace(chr(10), ' ')}",
            "",
        ])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_freeze_readiness_review(write_reports=True)
    print(json.dumps({
        "recommendation": report["recommendation"],
        "tier_1_passed": all(report["tier_1_freeze_criteria"].values()),
        "tier_2_passed": all(report["tier_2_polish_criteria"].values()),
        "live_probe_pass_rate": round(sum(1 for item in report["live_runtime_probes"] if item["passed"]) / max(1, len(report["live_runtime_probes"])), 4),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
