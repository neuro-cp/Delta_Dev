from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from orchestration.runtime.v15_explicit_canonical_memory_write_trial import DEFAULT_TRIAL_STORE
from orchestration.runtime.v16_canonical_memory_rollback_trial import is_canonical_trial_record_rolled_back


RUNTIME_V17A_RECALL_ROUTER_FLAGS: dict[str, bool] = {
    "limited_general_recall_router_design_enabled": True,
    "general_recall_active": False,
    "candidate_context_only": True,
    "provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class GeneralRecallSourceKind(str, Enum):
    V15I_TRIAL_RECORD = "v15i_trial_record"
    STATIC_REPO_LOCAL = "static_repo_local"
    EVALUATOR_ADVISORY = "evaluator_advisory"


@dataclass(frozen=True)
class GeneralRecallRouteRequest:
    request_id: str
    query: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class GeneralRecallSourcePolicy:
    policy_id: str
    allowed_sources: tuple[str, ...]
    disallowed_sources: tuple[str, ...]
    candidate_context_only: bool = True

    def as_dict(self) -> dict[str, object]:
        return {"policy_id": self.policy_id, "allowed_sources": list(self.allowed_sources), "disallowed_sources": list(self.disallowed_sources), "candidate_context_only": self.candidate_context_only}


@dataclass(frozen=True)
class GeneralRecallRouteCandidate:
    candidate_id: str
    source_kind: GeneralRecallSourceKind
    text: str
    source_reference: str
    advisory_only: bool = True
    authoritative: bool = False
    candidate_context_only: bool = True

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["source_kind"] = self.source_kind.value
        return data


def route_limited_general_recall(query: str, *, trial_store: str | Path = DEFAULT_TRIAL_STORE, rollback_marker_path: str | Path = "data/runtime_v16j/canonical_trial_rollback_markers.jsonl") -> dict[str, object]:
    request = GeneralRecallRouteRequest(_stable_id("v17a-recall-request", query), query)
    policy = GeneralRecallSourcePolicy(
        _stable_id("v17a-policy", "candidate-only"),
        allowed_sources=("V1.5I canonical trial records", "static repo-local knowledge", "evaluator advisory reports"),
        disallowed_sources=("raw conversation as memory", "unapproved candidates as truth", "rejected or rolled-back records", "provider output as authority"),
    )
    candidates = _trial_record_candidates(Path(trial_store), Path(rollback_marker_path))
    candidates += _static_candidates(query)
    candidates += _evaluator_advisory_candidates()
    selected = [item for item in candidates if _matches(query, item.text)][:5]
    return {
        "phase": "Runtime V1.7A",
        "request": request.as_dict(),
        "source_policy": policy.as_dict(),
        "candidates": [item.as_dict() for item in selected],
        "safety_review": {
            "candidate_context_only": True,
            "provider_output_authority": False,
            "memory_write_performed": False,
            "recall_mutated": False,
            "training_triggered": False,
        },
        "invariant_flags": dict(RUNTIME_V17A_RECALL_ROUTER_FLAGS),
        "final_recommendation": "PROCEED_LOCAL_MULTI_TURN_SESSION_STATE",
    }


def validate_limited_general_recall_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    return (
        payload["safety_review"]["candidate_context_only"] is True
        and payload["safety_review"]["provider_output_authority"] is False
        and all(item["authoritative"] is False and item["candidate_context_only"] is True for item in payload["candidates"])
        and flags["limited_general_recall_router_design_enabled"] is True
        and flags["candidate_context_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"limited_general_recall_router_design_enabled", "candidate_context_only"})
    )


def _trial_record_candidates(path: Path, rollback_path: Path) -> list[GeneralRecallRouteCandidate]:
    if not path.exists():
        return []
    candidates = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        record_id = str(record.get("canonical_record_id", ""))
        if is_canonical_trial_record_rolled_back(record_id, rollback_path):
            continue
        candidates.append(
            GeneralRecallRouteCandidate(
                candidate_id=_stable_id("v17a-candidate", record_id),
                source_kind=GeneralRecallSourceKind.V15I_TRIAL_RECORD,
                text=str(record.get("record_text", "")),
                source_reference=record_id,
            )
        )
    return candidates


def _static_candidates(query: str) -> list[GeneralRecallRouteCandidate]:
    if "model b" in query.lower() or "hyb1" in query.lower():
        return [GeneralRecallRouteCandidate(_stable_id("v17a-static", "model-b"), GeneralRecallSourceKind.STATIC_REPO_LOCAL, "Model B remains default and HYB1 remains dormant/env-gated.", "static-local-router")]
    return []


def _evaluator_advisory_candidates() -> list[GeneralRecallRouteCandidate]:
    path = Path("reports/runtime_v16c_daily_external_consolidation_evaluator_api_trial.json")
    if not path.exists():
        return []
    try:
        review = json.loads(path.read_text(encoding="utf-8")).get("advisory_review", {})
    except json.JSONDecodeError:
        return []
    if not isinstance(review, dict):
        return []
    return [GeneralRecallRouteCandidate(_stable_id("v17a-advisory", review.get("review_id", "")), GeneralRecallSourceKind.EVALUATOR_ADVISORY, f"Advisory evaluator disposition: {review.get('disposition', '')}", str(path))]


def _matches(query: str, text: str) -> bool:
    q = query.lower()
    t = text.lower()
    return any(token in t for token in q.split() if len(token) > 3)


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
