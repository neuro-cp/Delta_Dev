"""Runtime V2.7E full local demo scaffold."""

from __future__ import annotations

import json
from pathlib import Path


REPORT_MD = Path("reports/runtime_v27e_full_local_demo.md")
REPORT_JSON = Path("reports/runtime_v27e_full_local_demo.json")


def build_full_local_demo() -> dict[str, object]:
    return {
        "phase": "Runtime V2.7E",
        "mode": "local_demo_report_only",
        "demo_steps": [
            "open local console",
            "ask repo-local knowledge question",
            "route through local answer router",
            "show safety status",
            "show blocked training/provider/action paths",
        ],
        "executed_steps": [],
        "safety_invariants": _safe_flags(),
        "final_recommendation": "PROCEED_MASTER_CONTINUATION_HANDOFF",
    }


def validate_full_local_demo_safe(data: dict[str, object]) -> bool:
    return data["executed_steps"] == [] and all(value is False for value in data["safety_invariants"].values())


def write_full_local_demo_report() -> dict[str, object]:
    data = build_full_local_demo()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(_render(data), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _safe_flags() -> dict[str, bool]:
    return {"provider_call_performed": False, "memory_write_performed": False, "training_performed": False, "action_execution_performed": False}


def _render(data: dict[str, object]) -> str:
    rows = "\n".join(f"- {step}" for step in data["demo_steps"])
    return f"# {data['phase']} Full Local Demo\n\nMode: {data['mode']}\n\n{rows}\n\nFinal recommendation: {data['final_recommendation']}\n"


if __name__ == "__main__":
    print(write_full_local_demo_report()["final_recommendation"])
