"""Fast RC2 validation smoke runner.

This script is the RC2 inner-loop validation path. It intentionally avoids the
full ``tests/runtime_rc2`` integration suite, which is now a release-checkpoint
battery. The checks here cover routing, retrieval, graph-assisted reasoning,
safety invariants, and existing JSON report readability without training,
provider calls, canonical writes, autonomous actions, or scheduler activity.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.rc2_conversational_mode_router import route_message
from orchestration.runtime.rc2_developmental_concept_memory import retrieve_multi_concept_set
from orchestration.runtime.rc2_graph_assisted_reasoning import build_graph_assisted_reasoning_trial


REPORTS = ROOT / "reports"

REPORTS_TO_VALIDATE = [
    "RC2_GRAPH_ASSISTED_REASONING_COMPLETION.json",
    "RC2_GOVERNED_SEMANTIC_GRAPH_COMPLETION.json",
    "RC2_TYPED_GRAPH_CONSISTENCY_CALIBRATION.json",
]

SAFETY_FALSE_KEYS = [
    "provider_calls_performed",
    "training_performed",
    "canonical_write_performed",
    "autonomous_action_performed",
]


def run_fast_validation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    conversation = route_message("Conversation", "What color is the sky?")
    checks.append(_check(
        "conversational_routing_smoke",
        conversation.get("mode") == "Conversation"
        and bool(conversation.get("answer"))
        and _payload_safety_ok(conversation),
        route=conversation.get("route"),
    ))

    retrieval = retrieve_multi_concept_set("How does photosynthesis relate to respiration?")
    checks.append(_check(
        "multi_concept_retrieval_smoke",
        retrieval.get("matched") is True
        and len(retrieval.get("matches", [])) >= 2
        and retrieval.get("synthesis_readiness") is False,
        match_count=len(retrieval.get("matches", [])),
        retrieval_set_quality=retrieval.get("retrieval_set_quality"),
    ))

    graph_reasoning = build_graph_assisted_reasoning_trial(
        "Use graph-assisted reasoning to explain how photosynthesis relates to respiration."
    )
    checks.append(_check(
        "graph_assisted_reasoning_smoke",
        graph_reasoning.get("route") == "read_only_graph_assisted_reasoning_trial"
        and graph_reasoning.get("read_only") is True
        and graph_reasoning.get("graph_write_performed") is False
        and graph_reasoning.get("reasoning_quality", {}).get("overall_score", 0.0) >= 0.70
        and _payload_safety_ok(graph_reasoning),
        reasoning_quality=graph_reasoning.get("reasoning_quality", {}).get("overall_score"),
    ))

    report_validation = _validate_reports()
    checks.append(_check(
        "json_report_validation_smoke",
        report_validation["valid"],
        validated_reports=report_validation["validated_reports"],
        missing_reports=report_validation["missing_reports"],
    ))

    safety = _aggregate_safety([conversation, graph_reasoning])
    checks.append(_check("safety_invariant_smoke", safety["passed"], safety_flags=safety["flags"]))

    passed = all(item["passed"] for item in checks)
    return {
        "phase": "RC2 Fast Validation",
        "passed": passed,
        "check_count": len(checks),
        "checks": checks,
        "full_runtime_rc2_suite_run": False,
        "recommended_inner_loop_command": r".\.venv311\Scripts\python.exe scripts\rc2_fast_validate.py",
        "recommended_final_checkpoint_command": r".\.venv311\Scripts\python.exe -m pytest tests\runtime_rc2 -q -ra",
        "safety": safety,
    }


def _check(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "details": details}


def _payload_safety_ok(payload: dict[str, Any]) -> bool:
    return all(payload.get(key) is False for key in SAFETY_FALSE_KEYS if key in payload)


def _aggregate_safety(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    flags = {
        "provider_calls_performed": False,
        "training_performed": False,
        "canonical_write_performed": False,
        "autonomous_action_performed": False,
        "web_search_performed": False,
        "scheduler_started": False,
        "hyb1_promoted": False,
        "model_b_replaced": False,
        "synthesis_enabled_by_default": False,
    }
    for payload in payloads:
        for key in flags:
            if payload.get(key) is True:
                flags[key] = True
        safety = payload.get("safety")
        if isinstance(safety, dict):
            for key in flags:
                if safety.get(key) is True:
                    flags[key] = True
    return {"passed": not any(flags.values()), "flags": flags}


def _validate_reports() -> dict[str, Any]:
    validated = []
    missing = []
    for name in REPORTS_TO_VALIDATE:
        path = REPORTS / name
        if not path.exists():
            missing.append(name)
            continue
        json.loads(path.read_text(encoding="utf-8"))
        validated.append(name)
    return {
        "valid": not missing,
        "validated_reports": validated,
        "missing_reports": missing,
    }


def main() -> int:
    result = run_fast_validation()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
