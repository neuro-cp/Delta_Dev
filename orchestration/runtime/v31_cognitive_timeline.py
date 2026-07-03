"""Runtime V3.1 cognitive timeline scaffold."""

from __future__ import annotations

import json
from pathlib import Path

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants


REPORT_MD = Path("reports/runtime_v31c_cognitive_timeline.md")
REPORT_JSON = Path("reports/runtime_v31c_cognitive_timeline.json")


TIMELINE_STAGES = (
    ("experience", "raw local interaction or observation", "available"),
    ("observation", "structured observation preview", "available"),
    ("learning_opportunity", "reviewable possible learning signal", "available"),
    ("proposal", "structured draft/review proposal", "available"),
    ("review", "human/operator review state", "available"),
    ("admin_approved_proposal", "approval marker that becomes eligible for gated integration", "available"),
    ("overwatch_or_override_gate", "overwatch allow/block or explicit owner override record", "available"),
    ("gated_integration_event", "audit/rollback event scaffold; no live write in V3.1", "available"),
    ("integration", "future live write only; not active", "future_only"),
    ("evaluation", "future only; not active", "future_only"),
    ("promotion", "future only; not active", "future_only"),
)


def build_cognitive_timeline() -> dict[str, object]:
    return {
        "phase": "Runtime V3.1C",
        "stops_at": "gated_integration_event_scaffold",
        "stages": [
            {"stage": name, "description": description, "status": status}
            for name, description, status in TIMELINE_STAGES
        ],
        "integration_active": False,
        "evaluation_active": False,
        "promotion_active": False,
        "safety_invariants": safety_invariants(),
        "final_recommendation": "PROCEED_CONTRADICTION_AGGREGATION",
    }


def write_cognitive_timeline_report() -> dict[str, object]:
    data = build_cognitive_timeline()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# Runtime V3.1C Cognitive Timeline", ""]
    for stage in data["stages"]:
        lines.append(f"- {stage['stage']}: {stage['description']} (`{stage['status']}`)")
    lines.append("")
    lines.append("Current runtime stops at: `gated_integration_event_scaffold`.")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    return data


if __name__ == "__main__":
    print(write_cognitive_timeline_report()["final_recommendation"])
