from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PROVIDER_REPORT = Path("reports/runtime_v18f_manual_provider_live_trial_optional_one_shot.json")

RUNTIME_V20F_FLAGS = {
    "provider_live_review_bridge_enabled": True,
    "live_provider_call_performed": False,
    "evaluator_cross_check_automatic": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def build_provider_live_review_bridge(report_path: str | Path = DEFAULT_PROVIDER_REPORT) -> dict[str, object]:
    path = Path(report_path)
    evidence: dict[str, object] | None = None
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        evidence = {
            "source_report": str(path),
            "evidence_only": True,
            "authoritative": False,
            "key_redacted": True,
            "summary": str(loaded.get("summary", loaded.get("phase", "provider evidence report"))),
        }
    return {
        "phase": "Runtime V2.0F",
        "provider_report_present": path.exists(),
        "provider_evidence": evidence,
        "quality_review_export": "ui/delta_quality_review_dashboard.html",
        "invariant_flags": dict(RUNTIME_V20F_FLAGS),
        "final_recommendation": "PROCEED_SCHEDULER_ACTIVATION_TRIAL_DESIGN_ONLY",
    }


def validate_provider_live_review_bridge_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    evidence = payload.get("provider_evidence")
    return (
        (evidence is None or (evidence["evidence_only"] is True and evidence["authoritative"] is False))
        and flags["provider_live_review_bridge_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "provider_live_review_bridge_enabled")
    )
