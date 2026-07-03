"""Runtime V2.6E feature activation gate console scaffold."""

from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v26e_feature_activation_gate_console.md")
REPORT_JSON = Path("reports/runtime_v26e_feature_activation_gate_console.json")


def build_feature_activation_gate_console() -> dict[str, object]:
    gates = {
        "memory_write": "approval_required",
        "recall_bridge": "disabled",
        "provider_live": "approval_required",
        "hyb1_shadow": "env_gated_dormant",
        "scheduler_dry_run": "approval_required",
        "training": "blocked",
        "action_execution": "blocked",
    }
    return {
        "phase": "Runtime V2.6E",
        "mode": "console_design_only",
        "gates": gates,
        "active_gate_changes": [],
        "safety_invariants": _safe_flags(),
        "final_recommendation": "PROCEED_V26_SAFETY_CHECKPOINT",
    }


def validate_feature_activation_gate_console_safe(data: dict[str, object]) -> bool:
    return not data["active_gate_changes"] and all(value is False for value in data["safety_invariants"].values())


def write_feature_activation_gate_console_report() -> dict[str, object]:
    data = build_feature_activation_gate_console()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _safe_flags() -> dict[str, bool]:
    return {
        "training_performed": False,
        "feature_activated": False,
        "hyb1_promoted": False,
        "provider_call_performed": False,
        "scheduler_started": False,
        "action_execution_performed": False,
    }


def _render(data: dict[str, object]) -> str:
    rows = "\n".join(f"- {name}: {state}" for name, state in data["gates"].items())
    return f"# {data['phase']} Feature Activation Gate Console\n\nMode: {data['mode']}\n\n{rows}\n\nFinal recommendation: {data['final_recommendation']}\n"


if __name__ == "__main__":
    print(write_feature_activation_gate_console_report()["final_recommendation"])
