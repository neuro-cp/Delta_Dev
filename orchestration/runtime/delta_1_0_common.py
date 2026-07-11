"""Shared DELTA 1.0 operator-pilot primitives.

This module is deliberately inert. It provides deterministic identifiers,
report helpers, and safety metadata for the post-RC operator pilot foundation.
It does not execute plans, call providers, persist hidden state, activate
plugins, or mutate production systems.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "delta_1_0"
REPORT_DIR = ROOT / "reports" / "delta_1_0"


SAFETY_FALSES: dict[str, bool] = {
    "provider_calls_performed": False,
    "network_calls_performed": False,
    "external_retrieval_performed": False,
    "training_performed": False,
    "fine_tuning_performed": False,
    "weight_update_performed": False,
    "canonical_write_performed": False,
    "noncanonical_write_performed": False,
    "developmental_memory_write_performed": False,
    "hidden_persistence_performed": False,
    "scheduler_action_performed": False,
    "autonomous_action_performed": False,
    "automatic_approval_performed": False,
    "automatic_code_modification_performed": False,
    "runtime_commit_performed": False,
    "runtime_push_performed": False,
    "deployment_performed": False,
    "plugin_activation_performed": False,
    "sandbox_creation_performed": False,
    "production_mutation_performed": False,
    "delta_75_interaction_performed": False,
}


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_id(prefix: str, *parts: Any) -> str:
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def safety_metadata() -> dict[str, bool]:
    return dict(SAFETY_FALSES)


def jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: jsonable(val) for key, val in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): jsonable(val) for key, val in value.items()}
    if isinstance(value, tuple | list):
        return [jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted(jsonable(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jsonable(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, title: str, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        lines.append(f"## {key.replace('_', ' ').title()}")
        if isinstance(value, Mapping):
            for subkey, subvalue in value.items():
                lines.append(f"- **{subkey}**: {json.dumps(jsonable(subvalue), sort_keys=True)}")
        elif isinstance(value, tuple | list):
            for item in value:
                lines.append(f"- {json.dumps(jsonable(item), sort_keys=True)}")
        else:
            lines.append(str(value))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def bounds_report(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "authority": "operator_governed_inert_foundation",
        "provider_calls": False,
        "network_calls": False,
        "automatic_execution": False,
        "automatic_code_modification": False,
        "automatic_commit_push": False,
        "hidden_persistence": False,
        "delta_75_scope": False,
        "safety": safety_metadata(),
    }
