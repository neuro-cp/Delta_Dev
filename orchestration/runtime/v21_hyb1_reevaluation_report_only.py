from __future__ import annotations

import hashlib
from pathlib import Path


RUNTIME_V21E_FLAGS = {
    "hyb1_reevaluation_report_only_enabled": True,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
    "routing_default_changed": False,
    "provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
}


def reevaluate_hyb1_report_only() -> dict[str, object]:
    evidence_inputs = {
        "v20_summary": Path("reports/runtime_v20a_v20h_marathon_summary.md").exists(),
        "v20_safety": Path("reports/runtime_v20h_v20_safety_checkpoint_report.md").exists(),
        "v18_quality": Path("reports/runtime_v18d_local_review_ui_iteration_for_evidence_quality.md").exists(),
        "promotion_readiness": Path("reports/runtime_v18c_promotion_readiness_scorecard.json").exists(),
    }
    blockers = ["HYB1 remains dormant/env-gated", "report-only re-evaluation cannot promote", "future human review required before any default change"]
    scorecard = {
        "scorecard_id": _stable_id("v21e-hyb1-scorecard", evidence_inputs),
        "evidence_inputs": evidence_inputs,
        "current_status": "dormant_env_gated",
        "model_b_status": "default_unchanged",
        "promotion_readiness_status": "report_only_no_change",
        "blockers": blockers,
        "supported_outcome": "keep_dormant",
    }
    return {
        "phase": "Runtime V2.1E",
        "scorecard": scorecard,
        "recommendation": "keep_dormant",
        "invariant_flags": dict(RUNTIME_V21E_FLAGS),
        "final_recommendation": "PROCEED_V21_SAFETY_CHECKPOINT_REPORT",
    }


def validate_hyb1_reevaluation_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["recommendation"] in {"keep_dormant", "requires_more_evidence", "eligible_for_future_human_review", "blocked_by_safety", "blocked_by_insufficient_evidence", "report_only_no_change"}
        and flags["hyb1_reevaluation_report_only_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "hyb1_reevaluation_report_only_enabled")
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
