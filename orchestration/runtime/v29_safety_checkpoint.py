"""Runtime V2.9F self-description safety checkpoint."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import build_current_state_inventory, safety_invariants


REPORT_MD = Path("reports/runtime_v29f_self_description_safety_checkpoint.md")
REPORT_JSON = Path("reports/runtime_v29f_self_description_safety_checkpoint.json")
DOC = Path("docs/continuation_runtime_v29_self_description.md")


def build_v29_safety_checkpoint() -> dict[str, object]:
    inventory = build_current_state_inventory()
    return {
        "phase": "Runtime V2.9F",
        "completed_phases": ["V2.9A", "V2.9B", "V2.9C", "V2.9D", "V2.9E", "V2.9F"],
        "active_capabilities": inventory["active_local_capabilities"],
        "disabled_capabilities": inventory["disabled_capabilities"],
        "known_blockers": inventory["known_blockers"],
        "safety_state": {
            "model_b_default": "unchanged",
            "hyb1": "dormant_env_gated_shadow_only",
            "training": "disabled",
            "provider_calls": "disabled",
            "memory_writes": "disabled",
            "recall": "candidate_context_only",
            "scheduler": "disabled",
        },
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_MANUAL_LOCAL_DEMO_AND_SELECTED_CLEANUP_REVIEW",
    }


def validate_v29_safety_checkpoint_safe(data: dict[str, object]) -> bool:
    return data["safety_state"]["model_b_default"] == "unchanged" and all(value is False for value in data["safety_invariants"].values())


def write_v29_safety_checkpoint_report() -> dict[str, object]:
    data = build_v29_safety_checkpoint()
    if not validate_v29_safety_checkpoint_safe(data):
        raise RuntimeError("Unsafe V2.9 safety checkpoint")
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    text = _render(data)
    REPORT_MD.write_text(text, encoding="utf-8")
    DOC.write_text(text, encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _render(data: dict[str, object]) -> str:
    return f"""# Runtime V2.9F Self-Description Safety Checkpoint

Completed phases: {', '.join(data['completed_phases'])}

Model B: {data['safety_state']['model_b_default']}

HYB1: {data['safety_state']['hyb1']}

Training: {data['safety_state']['training']}

Provider calls: {data['safety_state']['provider_calls']}

Memory writes: {data['safety_state']['memory_writes']}

Recall: {data['safety_state']['recall']}

Scheduler: {data['safety_state']['scheduler']}

Final recommendation: `{data['final_recommendation']}`
"""


if __name__ == "__main__":
    print(write_v29_safety_checkpoint_report()["final_recommendation"])
