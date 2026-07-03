from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v20_controlled_general_memory_trial import (
    APPROVAL_HEADER,
    parse_controlled_memory_approval,
    run_controlled_general_memory_trial,
)


RUNTIME_V21B_FLAGS = {
    "controlled_general_memory_expansion_enabled": True,
    "dry_run_default": True,
    "autonomous_write_allowed": False,
    "provider_direct_write_allowed": False,
    "memory_write_performed_without_explicit_approval": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


class ExpandedCandidateSourceKind(str, Enum):
    FEEDBACK_MEMORY_CANDIDATE = "v15g_feedback_memory_candidate"
    SESSION_TO_CANDIDATE = "v19d_session_to_candidate"
    UI_APPROVAL_EXPORT = "v20d_ui_approval_export"
    EDITED_MEMORY_CANDIDATE = "edited_memory_candidate"
    PROVIDER_EVIDENCE_CONVERTED = "provider_evidence_converted_to_candidate"


@dataclass(frozen=True)
class ExpandedMemoryCandidateSource:
    candidate_id: str
    source_kind: ExpandedCandidateSourceKind
    proposed_memory_text: str
    provenance_reference_ids: tuple[str, ...]
    approved: bool = False
    rejected: bool = False
    deferred: bool = False
    rolled_back: bool = False
    ambiguity_flag: bool = False
    sarcasm_flag: bool = False
    misuse_flag: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["source_kind"] = self.source_kind.value
        data["provenance_reference_ids"] = list(self.provenance_reference_ids)
        return data


def list_expanded_memory_candidates() -> list[dict[str, object]]:
    candidates = [
        ExpandedMemoryCandidateSource(
            "memory-candidate-demo",
            ExpandedCandidateSourceKind.UI_APPROVAL_EXPORT,
            "HYB1 remains dormant and Model B remains the default runtime baseline.",
            ("data/runtime_v20d/approval_exports/memory-candidate-demo.approve.txt",),
            approved=True,
        ),
        ExpandedMemoryCandidateSource(
            "session-candidate-demo",
            ExpandedCandidateSourceKind.SESSION_TO_CANDIDATE,
            "Provider evidence remains evidence-only until converted into a reviewed memory candidate.",
            ("reports/runtime_v19d_session_to_candidate_memory_proposal_flow.md",),
        ),
        ExpandedMemoryCandidateSource(
            "ambiguous-candidate-demo",
            ExpandedCandidateSourceKind.EDITED_MEMORY_CANDIDATE,
            "Maybe remember this if it seems right.",
            ("manual_edit",),
            ambiguity_flag=True,
        ),
    ]
    return [candidate.as_dict() for candidate in candidates]


def check_expanded_memory_write_eligibility(candidate_id: str, approval_text: str = "") -> dict[str, object]:
    candidate = _find_candidate(candidate_id)
    approval = parse_controlled_memory_approval(approval_text)
    blocks: list[str] = []
    if candidate is None:
        blocks.append("candidate_not_found")
    else:
        if candidate.get("rejected") or candidate.get("deferred") or candidate.get("rolled_back"):
            blocks.append("candidate_state_blocked")
        if candidate.get("ambiguity_flag") or candidate.get("sarcasm_flag") or candidate.get("misuse_flag"):
            blocks.append("ambiguity_sarcasm_or_misuse_flag")
        if not candidate.get("provenance_reference_ids"):
            blocks.append("missing_provenance")
    if not approval.get("matches_required_shape") or approval.get("candidate_id") != candidate_id:
        blocks.append("exact_approval_required")
    eligible = not blocks
    return {
        "eligibility_id": _stable_id("v21b-eligibility", candidate_id, blocks),
        "candidate_id": candidate_id,
        "eligible": eligible,
        "blocks": blocks,
        "approval": approval,
    }


def run_expanded_memory_write_trial(candidate_id: str, approval_text: str = "", *, write: bool = False) -> dict[str, object]:
    candidate = _find_candidate(candidate_id)
    eligibility = check_expanded_memory_write_eligibility(candidate_id, approval_text)
    if not candidate or not eligibility["eligible"]:
        return _payload(candidate_id, eligibility, None, "blocked")
    result = run_controlled_general_memory_trial(candidate, approval_text, write=write)
    return _payload(candidate_id, eligibility, result, result["result"]["outcome"])


def validate_memory_expansion_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    trial = payload.get("controlled_trial_result")
    trial_safe = trial is None or (
        trial["result"]["recall_mutated"] is False
        and trial["result"]["training_triggered"] is False
        and trial["result"]["provider_call_performed"] is False
        and trial["result"]["autonomous_write"] is False
    )
    return (
        trial_safe
        and flags["controlled_general_memory_expansion_enabled"] is True
        and flags["dry_run_default"] is True
        and all(value is False for key, value in flags.items() if key not in {"controlled_general_memory_expansion_enabled", "dry_run_default"})
    )


def read_approval_file(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def _find_candidate(candidate_id: str) -> dict[str, object] | None:
    for candidate in list_expanded_memory_candidates():
        if candidate["candidate_id"] == candidate_id:
            return candidate
    return None


def _payload(candidate_id: str, eligibility: dict[str, object], trial: dict[str, object] | None, outcome: str) -> dict[str, object]:
    return {
        "phase": "Runtime V2.1B",
        "candidate_id": candidate_id,
        "eligibility": eligibility,
        "controlled_trial_result": trial,
        "decision": {
            "decision_id": _stable_id("v21b-decision", candidate_id, outcome),
            "outcome": outcome,
            "audit_required": True,
            "rollback_reference_required": True,
            "one_record_per_approval": True,
            "bulk_approval_allowed": False,
        },
        "invariant_flags": dict(RUNTIME_V21B_FLAGS),
        "final_recommendation": "PROCEED_PROVIDER_LIVE_TRIAL_USER_APPROVED",
    }


def approval_text_for_candidate(candidate_id: str) -> str:
    return f"{APPROVAL_HEADER}\ncandidate_id={candidate_id}\napproved_by=user\napproval_scope=single_memory_candidate_only"


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
