"""Shared helpers for DELTA post-ARC XXV deepening modules."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from orchestration.runtime.arc_exhaustive_common import deterministic_id, exhaustive_safety_flags, validate_no_authority


@dataclass(frozen=True)
class DeepeningValidation:
    valid: bool
    object_count: int
    graph_export_available: bool
    json_export_available: bool
    mutation_performed: bool = False
    provider_call_performed: bool = False
    scheduler_started: bool = False
    execution_performed: bool = False
    training_performed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DeepeningAudit:
    audit_id: str
    module_id: str
    status: str
    review_state: str
    authority: str
    safety_verified: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def ensure_jsonable(payload: dict[str, Any]) -> bool:
    json.dumps(payload, sort_keys=True)
    return True


def render_deepening_report(payload: dict[str, Any]) -> str:
    objects = "\n".join(f"- `{item['name']}`: {item['purpose']}" for item in payload["objects"])
    return f"""# {payload['batch_label']} {payload['title']}

## Summary

{payload['purpose']}

Status: `{payload['status']}`

## Objects

{objects}

## Validation

- Valid: {payload['validation']['valid']}
- Object count: {payload['validation']['object_count']}
- Graph export available: {payload['validation']['graph_export_available']}
- JSON export available: {payload['validation']['json_export_available']}

## Safety

- Model B default: {payload['safety']['model_b_default']}
- HYB1: {payload['safety']['hyb1']}
- Training performed: {payload['safety']['training_performed']}
- Provider authority granted: {payload['safety']['provider_authority_granted']}
- Scheduler started: {payload['safety']['scheduler_started']}
- Memory mutation performed: {payload['safety']['memory_mutation_performed']}
- Knowledge mutation performed: {payload['safety']['knowledge_mutation_performed']}

Recommendation: `{payload['recommendation']}`
"""


def render_deepening_dashboard(payload: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>{payload['module_id']}</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:32px;background:#f8fafc;color:#182230}}section{{background:white;border:1px solid #d8e0ec;border-radius:8px;padding:18px;margin:14px 0}}pre{{white-space:pre-wrap}}</style></head>
<body>
<h1>{payload['batch_label']} {payload['title']}</h1>
<section><h2>Objects</h2><pre>{json.dumps(payload['objects'], indent=2)}</pre></section>
<section><h2>Graph Metadata</h2><pre>{json.dumps(payload['graph_export_metadata'], indent=2)}</pre></section>
<section><h2>Safety</h2><pre>{json.dumps(payload['safety'], indent=2)}</pre></section>
</body></html>
"""


def write_deepening_artifacts(payload: dict[str, Any], base: str) -> dict[str, str]:
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("ui").mkdir(parents=True, exist_ok=True)
    md = Path(f"reports/{base}.md")
    js = Path(f"reports/{base}.json")
    html = Path(f"ui/{base}.html")
    md.write_text(render_deepening_report(payload), encoding="utf-8")
    js.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    html.write_text(render_deepening_dashboard(payload), encoding="utf-8")
    return {"markdown": str(md), "json": str(js), "dashboard": str(html)}
