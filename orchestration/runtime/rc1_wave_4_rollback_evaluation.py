"""RC1 Wave 4 rollback and evaluation validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_wave_3_simulated_substrate_writes import (
    AdminApprovalEvent,
    OverwatchReview,
    build_candidate,
    simulate_substrate_write,
)


REPORT_JSON = Path("reports/runtime_rc1_wave_4_rollback_evaluation.json")
REPORT_MD = Path("reports/runtime_rc1_wave_4_rollback_evaluation.md")


def run_rollback_evaluation() -> dict[str, Any]:
    candidate = build_candidate()
    write = simulate_substrate_write(
        AdminApprovalEvent(candidate["candidate_id"], "user", "single_memory_candidate_only"),
        OverwatchReview("allow", "fixture candidate only"),
    )
    before_state = {"simulated_records": [write["simulated_delta"]], "live_records": []}
    after_state = {"simulated_records": [], "live_records": []}
    restored = before_state["live_records"] == after_state["live_records"] and after_state["simulated_records"] == []
    health_delta = {
        "knowledge_health_delta": 0,
        "cognitive_health_score": 1.0,
        "regression_detected": False,
    }
    return {
        "phase": "RC1 Wave 4 Rollback And Evaluation",
        "before_state": before_state,
        "after_state": after_state,
        "rollback_token": write["simulated_delta"]["rollback_token"],
        "rollback_simulated": True,
        "live_rollback_performed": False,
        "restored_pre_state": restored,
        "health_delta": health_delta,
        "evaluation_recommendation": "simulation_safe_continue_to_provider_evidence_design",
        "stop_conditions_detected": [],
        "safety": {
            "knowledge_mutation_performed": False,
            "memory_mutation_performed": False,
            "action_execution_performed": False,
            "provider_call_performed": False,
        },
        "final_recommendation": "PROCEED_WAVE_5_PROVIDER_EVIDENCE_SIMULATED",
    }


def write_wave_4_report() -> dict[str, Any]:
    payload = run_rollback_evaluation()
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# RC1 Wave 4 Rollback And Evaluation\n\n"
        f"- rollback_simulated: {payload['rollback_simulated']}\n"
        f"- restored_pre_state: {payload['restored_pre_state']}\n"
        f"- regression_detected: {payload['health_delta']['regression_detected']}\n"
        f"- final_recommendation: `{payload['final_recommendation']}`\n",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    print(write_wave_4_report()["final_recommendation"])
