from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from orchestration.runtime.v20_controlled_general_memory_trial import run_controlled_general_memory_trial
from orchestration.runtime.v22_localhost_ui_mutation_bridge import parse_ui_mutation_event


RUNTIME_V23B_FLAGS = {
    "localhost_write_execution_bridge_enabled": True,
    "dry_run_default": True,
    "exact_approval_required": True,
    "bulk_approval_allowed": False,
    "hidden_write_allowed": False,
    "provider_call_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class LocalhostWriteExecutionRequest:
    request_id: str
    candidate_id: str
    write: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def run_localhost_write_execution_bridge(
    candidate: dict[str, object],
    approval_text: str,
    *,
    write: bool = False,
    record_store: str | Path = Path("data/runtime_v23b/ui_controlled_memory_records.jsonl"),
    audit_store: str | Path = Path("data/runtime_v23b/ui_controlled_memory_audit.jsonl"),
) -> dict[str, object]:
    candidate_id = str(candidate.get("candidate_id") or candidate.get("memory_candidate_id") or "")
    approval = parse_ui_mutation_event(approval_text)
    blocks: list[str] = []
    if not approval.get("approval_valid") or approval.get("header") != "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE":
        blocks.append("exact_localhost_approval_required")
    if approval.get("candidate_id") != candidate_id:
        blocks.append("candidate_id_mismatch")
    if candidate.get("bulk_candidate_ids"):
        blocks.append("bulk_approval_blocked")
    if candidate.get("ambiguous") or candidate.get("ambiguity_flag"):
        blocks.append("ambiguous_candidate_blocked")
    if candidate.get("misuse") or candidate.get("misuse_flag") or candidate.get("malicious_signal_flag"):
        blocks.append("misuse_candidate_blocked")
    trial = None
    if not blocks:
        trial = run_controlled_general_memory_trial(
            {
                "candidate_id": candidate_id,
                "proposed_memory_text": candidate.get("proposed_memory_text") or candidate.get("candidate_text") or "",
                "provenance_reference_ids": candidate.get("provenance_reference_ids", ()),
                "source_kind": candidate.get("source_kind", "memory_candidate"),
            },
            "\n".join((
                "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE",
                f"candidate_id={candidate_id}",
                "approved_by=user",
                "approval_scope=single_memory_candidate_only",
            )),
            write=write,
            record_store=record_store,
            audit_store=audit_store,
        )
    return {
        "phase": "Runtime V2.3B",
        "request": LocalhostWriteExecutionRequest(_stable_id("v23b-request", candidate_id, write), candidate_id, write).as_dict(),
        "approval": approval,
        "blocks": blocks,
        "controlled_trial": trial,
        "decision": {
            "write_attempted": not blocks,
            "record_written": bool(trial and trial["result"]["record_written"]),
            "dry_run": not write,
            "audit_created": bool(trial and trial["record"]),
            "rollback_reference_created": bool(trial and trial["record"]),
            "hidden_write": False,
            "bulk_write": False,
            "provider_call_performed": False,
            "recall_mutated": False,
            "training_triggered": False,
        },
        "invariant_flags": dict(RUNTIME_V23B_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_RECALL_TO_SYNTHESIS_INTEGRATION",
    }


def validate_localhost_write_execution_bridge_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["decision"]["hidden_write"] is False
        and payload["decision"]["bulk_write"] is False
        and payload["decision"]["provider_call_performed"] is False
        and payload["decision"]["recall_mutated"] is False
        and flags["localhost_write_execution_bridge_enabled"] is True
        and flags["dry_run_default"] is True
        and flags["exact_approval_required"] is True
        and all(value is False for key, value in flags.items() if key not in {"localhost_write_execution_bridge_enabled", "dry_run_default", "exact_approval_required"})
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
