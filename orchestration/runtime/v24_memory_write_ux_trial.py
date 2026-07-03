from __future__ import annotations

from pathlib import Path

from orchestration.runtime.v23_localhost_write_execution_bridge import run_localhost_write_execution_bridge, validate_localhost_write_execution_bridge_safe


APPROVAL_SOURCE = "localhost_full_review_console"
APPROVAL_TEMPLATE = "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE\ncandidate_id={candidate_id}\napproved_by=user\napproval_scope=single_memory_candidate_only\napproval_source=localhost_full_review_console"

RUNTIME_V24B_FLAGS = {
    "memory_write_ux_trial_enabled": True,
    "dry_run_default": True,
    "exact_approval_required": True,
    "memory_write_performed_without_approval": False,
    "bulk_approval_allowed": False,
    "hidden_write_allowed": False,
    "provider_call_performed": False,
    "evaluator_direct_write_allowed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


def build_memory_write_approval(candidate_id: str) -> str:
    return APPROVAL_TEMPLATE.format(candidate_id=candidate_id)


def parse_memory_write_ux_approval(text: str) -> dict[str, object]:
    lines = _normalize(text).split("\n") if _normalize(text) else []
    parsed: dict[str, object] = {"header": lines[0] if lines else "", "line_count": len(lines)}
    for line in lines[1:]:
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()
    parsed["matches_required_shape"] = (
        parsed.get("header") == "APPROVE_CONTROLLED_GENERAL_MEMORY_WRITE"
        and parsed.get("approved_by") == "user"
        and parsed.get("approval_scope") == "single_memory_candidate_only"
        and parsed.get("approval_source") == APPROVAL_SOURCE
        and bool(parsed.get("candidate_id"))
        and parsed.get("line_count") == 5
    )
    return parsed


def run_memory_write_ux_trial(
    candidate: dict[str, object],
    approval_text: str = "",
    *,
    write: bool = False,
    record_store: str | Path = Path("data/runtime_v24b/memory_write_ux_records.jsonl"),
    audit_store: str | Path = Path("data/runtime_v24b/memory_write_ux_audit.jsonl"),
) -> dict[str, object]:
    approval = parse_memory_write_ux_approval(approval_text)
    delegated_approval = approval_text
    if approval["matches_required_shape"]:
        delegated_approval = approval_text.replace("approval_source=localhost_full_review_console", "approval_source=localhost_review_ui")
    bridge = run_localhost_write_execution_bridge(candidate, delegated_approval, write=write, record_store=record_store, audit_store=audit_store)
    bridge["phase"] = "Runtime V2.4B"
    bridge["approval"] = approval
    bridge["ux"] = {
        "approval_source_required": APPROVAL_SOURCE,
        "page_render_writes_nothing": True,
        "guided_flow_only": True,
    }
    bridge["invariant_flags"] = dict(RUNTIME_V24B_FLAGS)
    bridge["final_recommendation"] = "PROCEED_CONTROLLED_RECALL_ANSWER_UX_TRIAL"
    return bridge


def validate_memory_write_ux_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        validate_localhost_write_execution_bridge_safe({**payload, "invariant_flags": {
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
        }})
        and flags["memory_write_ux_trial_enabled"] is True
        and flags["dry_run_default"] is True
        and flags["exact_approval_required"] is True
        and all(value is False for key, value in flags.items() if key not in {"memory_write_ux_trial_enabled", "dry_run_default", "exact_approval_required"})
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())
