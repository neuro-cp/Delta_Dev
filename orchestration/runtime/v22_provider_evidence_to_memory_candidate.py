from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum


RUNTIME_V22C_FLAGS = {
    "provider_evidence_to_candidate_enabled": True,
    "canonical_write_ready_default": False,
    "approved_default": False,
    "written_default": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "provider_call_performed": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


class EvidenceSourceKind(str, Enum):
    PROVIDER = "provider"
    SPECIALIST = "specialist"
    EVALUATOR = "evaluator"


@dataclass(frozen=True)
class ProviderEvidenceCandidateSource:
    source_id: str
    source_kind: EvidenceSourceKind
    evidence_text: str
    provenance_reference: str
    uncertainty: str = "unverified evidence"
    conflict_flag: bool = False
    unsafe_flag: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["source_kind"] = self.source_kind.value
        return data


def convert_provider_evidence_to_candidate(source: ProviderEvidenceCandidateSource) -> dict[str, object]:
    blocks: list[str] = []
    if not source.provenance_reference:
        blocks.append("missing_provenance")
    if source.conflict_flag:
        blocks.append("conflict_review_required")
    if source.unsafe_flag:
        blocks.append("unsafe_evidence_review_required")
    evaluator_advisory_only = source.source_kind is EvidenceSourceKind.EVALUATOR
    proposal = None
    if not blocks:
        proposal = {
            "memory_candidate_id": _stable_id("v22c-candidate", source.source_id, source.evidence_text),
            "candidate_text": " ".join(source.evidence_text.split()),
            "source_kind": source.source_kind.value,
            "provenance_reference_ids": [source.provenance_reference],
            "uncertainty": source.uncertainty,
            "human_approval_required": True,
            "canonical_write_ready": False,
            "approved": False,
            "written": False,
            "evaluator_advisory_only": evaluator_advisory_only,
        }
    return {
        "phase": "Runtime V2.2C",
        "source": source.as_dict(),
        "proposal": proposal,
        "safety_review": {
            "blocks": blocks,
            "review_required": bool(blocks) or evaluator_advisory_only,
        },
        "decision": {
            "candidate_created": proposal is not None,
            "canonical_write_performed": False,
            "recall_mutated": False,
            "provider_call_performed": False,
        },
        "invariant_flags": dict(RUNTIME_V22C_FLAGS),
        "final_recommendation": "PROCEED_EVALUATOR_ASSISTED_MEMORY_CANDIDATE_REVIEW",
    }


def validate_evidence_candidate_conversion_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    proposal = payload.get("proposal")
    proposal_safe = proposal is None or (proposal["canonical_write_ready"] is False and proposal["approved"] is False and proposal["written"] is False)
    return (
        proposal_safe
        and payload["decision"]["canonical_write_performed"] is False
        and flags["provider_evidence_to_candidate_enabled"] is True
        and all(value is False for key, value in flags.items() if key != "provider_evidence_to_candidate_enabled")
    )


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
