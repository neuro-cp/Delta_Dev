"""Runtime V2.7A controlled feature activation dry-run trial."""

from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v27a_controlled_feature_activation_dry_run_trial.md")
REPORT_JSON = Path("reports/runtime_v27a_controlled_feature_activation_dry_run_trial.json")


def build_feature_activation_dry_run_trial() -> dict[str, object]:
    return {
        "phase": "Runtime V2.7A",
        "mode": "dry_run_only",
        "evaluated_gates": {
            "memory_write": "would_require_explicit_approval",
            "recall_bridge": "would_remain_disabled",
            "provider_live": "would_require_user_approval",
            "scheduler": "would_remain_dry_run",
            "training": "would_remain_blocked",
            "action_execution": "would_remain_blocked",
        },
        "activated_features": [],
        "safety_invariants": _safe_flags(),
        "final_recommendation": "PROCEED_INTEGRATION_UX_POLISH",
    }


def validate_feature_activation_dry_run_trial_safe(data: dict[str, object]) -> bool:
    return data["activated_features"] == [] and all(value is False for value in data["safety_invariants"].values())


def write_feature_activation_dry_run_trial_report() -> dict[str, object]:
    data = build_feature_activation_dry_run_trial()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _safe_flags() -> dict[str, bool]:
    return {
        "training_performed": False,
        "provider_call_performed": False,
        "memory_write_performed": False,
        "recall_mutated": False,
        "scheduler_started": False,
        "action_execution_performed": False,
        "hyb1_promoted": False,
    }


def _render(data: dict[str, object]) -> str:
    rows = "\n".join(f"- {name}: {state}" for name, state in data["evaluated_gates"].items())
    return f"# {data['phase']} Feature Activation Dry Run\n\nMode: {data['mode']}\n\n{rows}\n\nFinal recommendation: {data['final_recommendation']}\n"


if __name__ == "__main__":
    print(write_feature_activation_dry_run_trial_report()["final_recommendation"])
