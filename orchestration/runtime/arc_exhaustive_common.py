"""Shared helpers for exhaustive DELTA ARC VII-XXV runtime modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from orchestration.runtime.v29_current_state_knowledge_inventory import safety_invariants as current_safety_invariants
from orchestration.runtime.v31_learning_opportunity import stable_v31_id

PROHIBITED_CAPABILITIES = (
    "training",
    "fine_tuning",
    "model_update",
    "provider_authority",
    "autonomous_browsing",
    "tool_execution",
    "scheduler_background_worker",
    "memory_mutation",
    "knowledge_mutation",
    "hyb1_promotion",
)


def exhaustive_safety_flags() -> dict[str, Any]:
    return {
        "model_b_default": "unchanged",
        "hyb1": "dormant_env_gated",
        "training_performed": False,
        "fine_tuning_performed": False,
        "model_update_performed": False,
        "provider_authority_granted": False,
        "provider_call_performed": False,
        "autonomous_browsing_performed": False,
        "tool_execution_performed": False,
        "action_execution_performed": False,
        "scheduler_started": False,
        "background_worker_started": False,
        "memory_mutation_performed": False,
        "knowledge_mutation_performed": False,
        "hidden_write_performed": False,
        "hyb1_promoted": False,
        "secret_printed": False,
        "runtime_safety_invariants": current_safety_invariants(),
    }


def deterministic_id(*parts: object) -> str:
    return stable_v31_id("post-arc-xxv", *[str(part) for part in parts])


def validate_no_authority(payload: dict[str, Any]) -> bool:
    safety = payload.get("safety", payload)
    return all(
        safety.get(key) is False
        for key in (
            "training_performed",
            "fine_tuning_performed",
            "model_update_performed",
            "provider_authority_granted",
            "provider_call_performed",
            "autonomous_browsing_performed",
            "tool_execution_performed",
            "action_execution_performed",
            "scheduler_started",
            "background_worker_started",
            "memory_mutation_performed",
            "knowledge_mutation_performed",
            "hidden_write_performed",
            "hyb1_promoted",
            "secret_printed",
        )
    )


def render_report(payload: dict[str, Any]) -> str:
    primitive_lines = "\n".join(f"- `{name}`" for name in payload["primitive_names"])
    return f"""# {payload['arc_label']} {payload['title']}

## Summary

{payload['purpose']}

Status: `{payload['status']}`

## Implemented Primitives

{primitive_lines}

## Validation

- Validated: {payload['validation']['valid']}
- Object count: {payload['validation']['object_count']}
- JSON serializable: {payload['validation']['json_serializable']}

## Safety

- Model B default: {payload['safety']['model_b_default']}
- HYB1: {payload['safety']['hyb1']}
- Training performed: {payload['safety']['training_performed']}
- Provider authority granted: {payload['safety']['provider_authority_granted']}
- Autonomous browsing performed: {payload['safety']['autonomous_browsing_performed']}
- Tool execution performed: {payload['safety']['tool_execution_performed']}
- Scheduler started: {payload['safety']['scheduler_started']}
- Memory mutation performed: {payload['safety']['memory_mutation_performed']}
- Knowledge mutation performed: {payload['safety']['knowledge_mutation_performed']}

Final recommendation: `{payload['final_recommendation']}`
"""


def render_dashboard(payload: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>{payload['arc_label']} {payload['title']}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f8fafc;color:#182230}}section{{background:white;border:1px solid #d8e0ec;border-radius:8px;padding:18px;margin:14px 0}}pre{{white-space:pre-wrap}}</style></head>
<body>
<h1>{payload['arc_label']} {payload['title']}</h1>
<section><h2>Purpose</h2><p>{payload['purpose']}</p></section>
<section><h2>Primitives</h2><pre>{json.dumps(payload['primitive_names'], indent=2)}</pre></section>
<section><h2>Demo</h2><pre>{json.dumps(payload['demo'], indent=2)}</pre></section>
<section><h2>Safety</h2><pre>{json.dumps(payload['safety'], indent=2)}</pre></section>
</body></html>
"""


def write_report_artifacts(payload: dict[str, Any], report_base: str, dashboard_path: str) -> dict[str, Path]:
    md_path = Path(f"reports/{report_base}.md")
    json_path = Path(f"reports/{report_base}.json")
    html_path = Path(dashboard_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_report(payload), encoding="utf-8")
    html_path.write_text(render_dashboard(payload), encoding="utf-8")
    return {"markdown": md_path, "json": json_path, "dashboard": html_path}
