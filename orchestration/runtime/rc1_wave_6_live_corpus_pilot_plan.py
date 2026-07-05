"""RC1 Wave 6 controlled live corpus pilot design.

This is a plan and dry-run checklist only. It does not ingest arbitrary user
directories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPORT_JSON = Path("reports/runtime_rc1_wave_6_live_corpus_pilot_plan.json")
REPORT_MD = Path("reports/runtime_rc1_wave_6_live_corpus_pilot_plan.md")


def build_live_corpus_pilot_plan() -> dict[str, Any]:
    return {
        "phase": "RC1 Wave 6 Controlled Live Corpus Pilot Plan",
        "activation_enabled": False,
        "dry_run_only": True,
        "allowed_file_types": [".txt", ".md"],
        "maximum_corpus_size_bytes": 250_000,
        "directory_allowlist_rules": [
            "operator supplies a local path explicitly",
            "path must not be repository root",
            "path must not include .env, key, credential, or secret-like names",
        ],
        "provenance_requirements": ["source path", "sha256 checksum", "parser version", "run id"],
        "sensitive_data_handling": ["skip secret-like files", "record skipped count", "run secret scan after output"],
        "rollback_delete_requirements": ["all outputs under .tmp/rc1_live_corpus_pilot/<run_id>", "delete run folder to rollback"],
        "operator_approval_checklist": [
            "confirm input directory",
            "confirm noncanonical output",
            "confirm max size",
            "confirm no provider calls",
        ],
        "live_activation_blockers": [
            "Wave 0 manual validation must pass",
            "Wave 1 fixture ingestion must pass",
            "secret scan must pass",
            "manual approval gate must be implemented",
        ],
        "safety": {
            "live_arbitrary_ingestion_performed": False,
            "provider_call_performed": False,
            "training_performed": False,
            "knowledge_mutation_performed": False,
            "memory_mutation_performed": False,
        },
        "final_recommendation": "PROCEED_WAVE_7_LEARNING_CONSOLIDATION_PILOT_PLAN",
    }


def write_wave_6_report() -> dict[str, Any]:
    payload = build_live_corpus_pilot_plan()
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "# RC1 Wave 6 Controlled Live Corpus Pilot Plan\n\n"
        f"- activation_enabled: {payload['activation_enabled']}\n"
        f"- dry_run_only: {payload['dry_run_only']}\n"
        f"- allowed_file_types: {', '.join(payload['allowed_file_types'])}\n"
        f"- final_recommendation: `{payload['final_recommendation']}`\n",
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    print(write_wave_6_report()["final_recommendation"])
