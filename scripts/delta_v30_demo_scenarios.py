"""Runtime V3.0 deterministic manual demo scenarios."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants
from orchestration.runtime.v30_conversational_answer_formatter import build_conversational_answer
from orchestration.runtime.v30_pipeline_explainer import build_pipeline_explanation


REPORT_MD = Path("reports/runtime_v30d_manual_demo_scenario_pack.md")
REPORT_JSON = Path("reports/runtime_v30d_manual_demo_scenario_pack.json")


SCENARIOS = (
    ("identity", "What is DELTA?", "concise"),
    ("capability_summary", "What can you do?", "detailed"),
    ("unknown_personal_fact", "What did I eat for breakfast yesterday?", "concise"),
    ("memory_write_request", "Can you remember my favorite color is blue?", "detailed"),
    ("hyb1_status", "Is HYB1 active?", "concise"),
    ("training_status", "Can you train yourself?", "concise"),
    ("replay_consolidation_path", "What is your replay and consolidation path?", "detailed"),
    ("full_pipeline_explanation", "Explain how you answered that.", "explain"),
)


def run_demo_scenarios() -> dict[str, object]:
    results = []
    for scenario_id, query, mode in SCENARIOS:
        if scenario_id == "full_pipeline_explanation":
            payload = build_pipeline_explanation("What is DELTA?")
            answer = payload["rendered_explanation"]
        else:
            payload = build_conversational_answer(query, mode=mode)
            answer = payload["formatted_answer"]
        results.append(
            {
                "scenario_id": scenario_id,
                "query": query,
                "mode": mode,
                "answer_preview": answer,
                "provider_call_performed": False,
                "memory_write_performed": False,
                "training_triggered": False,
                "action_execution_performed": False,
            }
        )
    return {
        "phase": "Runtime V3.0D",
        "scenario_count": len(results),
        "scenarios": results,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_SELECTED_CLEANUP_REVIEW",
    }


def write_demo_scenario_report() -> dict[str, object]:
    data = run_demo_scenarios()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# Runtime V3.0D Manual Demo Scenario Pack", ""]
    for scenario in data["scenarios"]:
        lines.append(f"## {scenario['scenario_id']}")
        lines.append("")
        lines.append(f"Query: `{scenario['query']}`")
        lines.append("")
        lines.append(scenario["answer_preview"])
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return data


if __name__ == "__main__":
    print(write_demo_scenario_report()["final_recommendation"])
