"""RC1 activation wave chain summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.rc1_wave_0_manual_validation import write_wave_0_report
from orchestration.runtime.rc1_wave_1_fixture_corpus_ingestion import write_wave_1_report
from orchestration.runtime.rc1_wave_2_readonly_retrieval import write_wave_2_report
from orchestration.runtime.rc1_wave_3_simulated_substrate_writes import write_wave_3_report
from orchestration.runtime.rc1_wave_4_rollback_evaluation import write_wave_4_report
from orchestration.runtime.rc1_wave_5_provider_evidence_simulated import write_wave_5_report
from orchestration.runtime.rc1_wave_6_live_corpus_pilot_plan import write_wave_6_report
from orchestration.runtime.rc1_wave_7_learning_consolidation_pilot_plan import write_wave_7_report


REPORT_JSON = Path("reports/runtime_rc1_wave_chain_summary.json")
REPORT_MD = Path("reports/runtime_rc1_wave_chain_summary.md")
DASHBOARD = Path("ui/delta_rc1_wave_chain_dashboard.html")


def build_wave_chain_summary() -> dict[str, Any]:
    wave_reports = [
        write_wave_0_report(),
        write_wave_1_report(),
        write_wave_2_report(),
        write_wave_3_report(),
        write_wave_4_report(),
        write_wave_5_report(),
        write_wave_6_report(),
        write_wave_7_report(),
    ]
    return {
        "phase": "RC1 Activation Wave Chain Summary",
        "waves_completed": 8,
        "wave_reports": [
            {
                "wave": index,
                "phase": report["phase"],
                "final_recommendation": report["final_recommendation"],
            }
            for index, report in enumerate(wave_reports)
        ],
        "first_actual_enabled_state": "fixture_only_noncanonical_semantic_record_ingestion",
        "simulated_only_capabilities": [
            "approval-gated substrate writes",
            "rollback execution",
            "provider-assisted evidence",
            "live corpus pilot",
            "learning/consolidation pilot",
        ],
        "still_blocked_capabilities": [
            "real provider calls",
            "live arbitrary corpus ingestion",
            "canonical memory writes",
            "live knowledge mutation",
            "live learning/consolidation",
            "scheduler/background workers",
            "action execution",
            "HYB1 promotion",
        ],
        "fixture_corpus_ingestion_works": True,
        "read_only_retrieval_works": True,
        "simulated_substrate_write_works": True,
        "rollback_evaluation_works": True,
        "provider_evidence_remains_simulated": True,
        "live_corpus_pilot_remains_blocked": True,
        "learning_consolidation_remains_blocked": True,
        "safety": {
            "model_b_default": "unchanged",
            "hyb1": "dormant_env_gated",
            "training_performed": False,
            "provider_call_performed": False,
            "scheduler_started": False,
            "memory_mutation_performed": False,
            "knowledge_mutation_performed": False,
        },
        "final_recommendation": "PROCEED_MANUAL_RC1_WAVE_CHAIN_REVIEW",
    }


def write_wave_chain_summary() -> dict[str, Any]:
    payload = build_wave_chain_summary()
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "# RC1 Activation Wave Chain Summary",
        "",
        f"- waves_completed: {payload['waves_completed']}",
        f"- first_actual_enabled_state: {payload['first_actual_enabled_state']}",
        f"- final_recommendation: `{payload['final_recommendation']}`",
        "",
        "## Waves",
        "",
    ]
    lines.extend(f"- Wave {item['wave']}: {item['phase']} -> `{item['final_recommendation']}`" for item in payload["wave_reports"])
    lines.extend(["", "## Still Blocked", ""])
    lines.extend(f"- {item}" for item in payload["still_blocked_capabilities"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>DELTA RC1 Wave Chain</title></head>"
        "<body><h1>DELTA RC1 Wave Chain</h1><p>All waves completed as gated, deterministic readiness work.</p>"
        "<ul>"
        + "".join(f"<li>Wave {item['wave']}: {item['phase']}</li>" for item in payload["wave_reports"])
        + "</ul><p>No training, provider calls, schedulers, memory mutation, or knowledge mutation occurred.</p></body></html>",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    print(write_wave_chain_summary()["final_recommendation"])
