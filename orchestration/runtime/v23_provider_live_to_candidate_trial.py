from __future__ import annotations

import hashlib
from dataclasses import dataclass

from orchestration.runtime.v21_provider_live_trial_user_approved import APPROVAL_TEXT as LIVE_APPROVAL_TEXT
from orchestration.runtime.v21_provider_live_trial_user_approved import run_user_approved_provider_live_trial
from orchestration.runtime.v22_provider_evidence_to_memory_candidate import EvidenceSourceKind, ProviderEvidenceCandidateSource, convert_provider_evidence_to_candidate


CONVERSION_APPROVAL_TEXT = "APPROVE_PROVIDER_EVIDENCE_TO_MEMORY_CANDIDATE\napproved_by=user\ncandidate_scope=single_provider_evidence_packet_only"

RUNTIME_V23D_FLAGS = {
    "provider_live_to_candidate_trial_enabled": True,
    "dry_run_default": True,
    "provider_output_authoritative": False,
    "canonical_write_ready_default": False,
    "approved_default": False,
    "written_default": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "action_execution_performed": False,
    "scheduler_started": False,
    "hyb1_default_activation_enabled": False,
    "model_b_default_changed": False,
}


@dataclass(frozen=True)
class ProviderLiveToCandidateRequest:
    request_id: str
    question: str
    live_provider: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def parse_provider_candidate_conversion_approval(text: str) -> dict[str, object]:
    normalized = _normalize(text)
    return {"approval_present": bool(normalized), "matches_required_shape": normalized == _normalize(CONVERSION_APPROVAL_TEXT)}


def run_provider_live_to_candidate_trial(
    question: str,
    *,
    live_approval_text: str = "",
    conversion_approval_text: str = "",
    live_provider: bool = False,
    env: dict[str, str] | None = None,
    transport=None,
) -> dict[str, object]:
    provider = run_user_approved_provider_live_trial(question, approval_text=live_approval_text, live_provider=live_provider, env=env or {}, transport=transport)
    conversion_approval = parse_provider_candidate_conversion_approval(conversion_approval_text)
    evidence = provider.get("provider_evidence_packet")
    blocks: list[str] = []
    candidate = None
    if not evidence:
        blocks.append("provider_evidence_unavailable")
    if not conversion_approval["matches_required_shape"]:
        blocks.append("exact_conversion_approval_required")
    if evidence and conversion_approval["matches_required_shape"]:
        source = ProviderEvidenceCandidateSource(
            source_id=str(evidence.get("packet_id", _stable_id("v23d-evidence", question))),
            source_kind=EvidenceSourceKind.PROVIDER,
            evidence_text=str(evidence.get("answer_text") or evidence.get("text") or ""),
            provenance_reference=str(evidence.get("provenance", "provider-live-trial")),
            uncertainty=str(evidence.get("uncertainty", "unverified provider evidence")),
        )
        candidate = convert_provider_evidence_to_candidate(source)
    return {
        "phase": "Runtime V2.3D",
        "request": ProviderLiveToCandidateRequest(_stable_id("v23d-request", question, live_provider), question, live_provider).as_dict(),
        "provider_trial": provider,
        "conversion_approval": conversion_approval,
        "blocks": blocks,
        "candidate_conversion": candidate,
        "decision": {
            "provider_call_performed": bool(provider["decision"]["provider_call_performed"]),
            "candidate_created": bool(candidate and candidate["decision"]["candidate_created"]),
            "canonical_write_performed": False,
            "recall_mutated": False,
            "training_triggered": False,
            "action_execution_performed": False,
        },
        "invariant_flags": dict(RUNTIME_V23D_FLAGS),
        "final_recommendation": "PROCEED_DAILY_EVALUATOR_SCHEDULED_DRY_RUN_TRIAL",
    }


def validate_provider_live_to_candidate_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    candidate = payload.get("candidate_conversion")
    proposal = candidate.get("proposal") if candidate else None
    return (
        (proposal is None or (proposal["canonical_write_ready"] is False and proposal["approved"] is False and proposal["written"] is False))
        and payload["decision"]["canonical_write_performed"] is False
        and payload["decision"]["recall_mutated"] is False
        and flags["provider_live_to_candidate_trial_enabled"] is True
        and flags["dry_run_default"] is True
        and flags["provider_output_authoritative"] is False
        and all(value is False for key, value in flags.items() if key not in {"provider_live_to_candidate_trial_enabled", "dry_run_default", "provider_output_authoritative"})
    )


def _normalize(text: str) -> str:
    return "\n".join(line.strip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip())


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"

