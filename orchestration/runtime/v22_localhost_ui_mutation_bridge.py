from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


APPROVE_HEADER = "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE"
REJECT_HEADER = "REJECT_MEMORY_CANDIDATE"
DEFER_HEADER = "DEFER_MEMORY_CANDIDATE"
EXPORT_DIR = Path("data/runtime_v22a/ui_mutation_exports")

RUNTIME_V22A_FLAGS: dict[str, bool] = {
    "localhost_ui_mutation_bridge_enabled": True,
    "dry_run_default": True,
    "hidden_ui_writes_allowed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "scheduler_started": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class LocalhostUIEventKind(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"


@dataclass(frozen=True)
class LocalhostUIMutationBridgeRequest:
    request_id: str
    candidate_id: str
    event_kind: LocalhostUIEventKind
    dry_run: bool = True

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["event_kind"] = self.event_kind.value
        return data


@dataclass(frozen=True)
class LocalhostUIMutationBridgeDecision:
    decision_id: str
    event_valid: bool
    export_written: bool
    backend_memory_write_performed: bool = False
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def build_ui_mutation_event(candidate_id: str, event_kind: LocalhostUIEventKind) -> str:
    if event_kind is LocalhostUIEventKind.APPROVE:
        return "\n".join((
            APPROVE_HEADER,
            f"candidate_id={candidate_id}",
            "approved_by=user",
            "approval_scope=single_memory_candidate_only",
            "approval_source=localhost_review_ui",
        ))
    if event_kind is LocalhostUIEventKind.REJECT:
        return "\n".join((
            REJECT_HEADER,
            f"candidate_id={candidate_id}",
            "rejected_by=user",
            "rejection_scope=single_memory_candidate_only",
            "rejection_source=localhost_review_ui",
        ))
    return "\n".join((
        DEFER_HEADER,
        f"candidate_id={candidate_id}",
        "deferred_by=user",
        "defer_scope=single_memory_candidate_only",
        "defer_source=localhost_review_ui",
    ))


def parse_ui_mutation_event(text: str) -> dict[str, object]:
    lines = _normalize(text).split("\n") if _normalize(text) else []
    parsed: dict[str, object] = {"header": lines[0] if lines else "", "line_count": len(lines)}
    for line in lines[1:]:
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
    parsed["approval_valid"] = (
        parsed.get("header") == APPROVE_HEADER
        and parsed.get("approved_by") == "user"
        and parsed.get("approval_scope") == "single_memory_candidate_only"
        and parsed.get("approval_source") == "localhost_review_ui"
        and bool(parsed.get("candidate_id"))
        and parsed.get("line_count") == 5
    )
    parsed["reject_valid"] = (
        parsed.get("header") == REJECT_HEADER
        and parsed.get("rejected_by") == "user"
        and parsed.get("rejection_scope") == "single_memory_candidate_only"
        and parsed.get("rejection_source") == "localhost_review_ui"
        and bool(parsed.get("candidate_id"))
        and parsed.get("line_count") == 5
    )
    parsed["defer_valid"] = (
        parsed.get("header") == DEFER_HEADER
        and parsed.get("deferred_by") == "user"
        and parsed.get("defer_scope") == "single_memory_candidate_only"
        and parsed.get("defer_source") == "localhost_review_ui"
        and bool(parsed.get("candidate_id"))
        and parsed.get("line_count") == 5
    )
    parsed["machine_readable"] = parsed["approval_valid"] or parsed["reject_valid"] or parsed["defer_valid"]
    return parsed


def run_ui_mutation_bridge(candidate_id: str, event_kind: LocalhostUIEventKind, *, dry_run: bool = True, export_dir: str | Path = EXPORT_DIR) -> dict[str, object]:
    request = LocalhostUIMutationBridgeRequest(_stable_id("v22a-request", candidate_id, event_kind.value, dry_run), candidate_id, event_kind, dry_run)
    event_text = build_ui_mutation_event(candidate_id, event_kind)
    parsed = parse_ui_mutation_event(event_text)
    export_written = False
    if not dry_run:
        target = Path(export_dir)
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{candidate_id}.{event_kind.value}.txt").write_text(event_text, encoding="utf-8")
        export_written = True
    decision = LocalhostUIMutationBridgeDecision(
        _stable_id("v22a-decision", candidate_id, event_kind.value, export_written),
        bool(parsed["machine_readable"]),
        export_written,
        False,
        "export_only_no_backend_write",
    )
    return {
        "phase": "Runtime V2.2A",
        "request": request.as_dict(),
        "event_text": event_text,
        "parsed_event": parsed,
        "decision": decision.as_dict(),
        "audit_record": {
            "audit_id": _stable_id("v22a-audit", decision.decision_id),
            "hidden_write": False,
            "provider_call_performed": False,
            "recall_mutated": False,
        },
        "invariant_flags": dict(RUNTIME_V22A_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_GENERAL_RECALL_EXPANSION",
    }


def validate_ui_mutation_bridge_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["decision"]["backend_memory_write_performed"] is False
        and flags["localhost_ui_mutation_bridge_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"localhost_ui_mutation_bridge_enabled", "dry_run_default"})
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
