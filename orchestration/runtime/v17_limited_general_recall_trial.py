from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

from orchestration.runtime.v15_local_knowledge_router import route_local_knowledge_answer
from orchestration.runtime.v17_limited_general_recall_router import route_limited_general_recall


RUNTIME_V17F_FLAGS: dict[str, bool] = {
    "limited_general_recall_trial_enabled": True,
    "candidate_context_only": True,
    "general_memory_active": False,
    "authoritative_recall_enabled": False,
    "provider_call_performed": False,
    "memory_write_performed": False,
    "recall_mutated": False,
    "training_triggered": False,
    "scheduler_enabled": False,
    "hyb1_default_activation_enabled": False,
    "hyb1_promoted": False,
    "model_b_default_changed": False,
}


class LimitedGeneralRecallSourceKind(str, Enum):
    V15I_CANONICAL_TRIAL = "v15i_canonical_trial_record"
    LOCAL_STATIC = "local_static_knowledge"
    EVALUATOR_ADVISORY = "evaluator_advisory"
    PROVIDER_EVIDENCE = "provider_evidence_only"
    SPECIALIST_EVIDENCE = "specialist_evidence_only"


@dataclass(frozen=True)
class LimitedGeneralRecallTrialRequest:
    request_id: str
    query: str
    max_candidates: int = 3

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class LimitedGeneralRecallSourceSnapshot:
    snapshot_id: str
    allowed_sources: tuple[str, ...]
    disallowed_sources: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"snapshot_id": self.snapshot_id, "allowed_sources": list(self.allowed_sources), "disallowed_sources": list(self.disallowed_sources)}


@dataclass(frozen=True)
class LimitedGeneralRecallCandidate:
    candidate_id: str
    source_kind: LimitedGeneralRecallSourceKind
    text: str
    provenance: str
    rank: int
    candidate_context_only: bool = True
    authoritative: bool = False
    rejected_or_rolled_back: bool = False

    def as_dict(self) -> dict[str, object]:
        data = self.__dict__.copy()
        data["source_kind"] = self.source_kind.value
        return data


@dataclass(frozen=True)
class LimitedGeneralRecallDecision:
    decision_id: str
    selected_count: int
    max_candidates: int
    candidate_context_only: bool = True
    memory_write_performed: bool = False
    recall_mutated: bool = False
    provider_call_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class LimitedGeneralRecallSafetyStatus:
    safety_status_id: str
    safe: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class LimitedGeneralRecallTrace:
    trace_id: str
    request: LimitedGeneralRecallTrialRequest
    source_snapshot: LimitedGeneralRecallSourceSnapshot
    candidates: tuple[LimitedGeneralRecallCandidate, ...]
    decision: LimitedGeneralRecallDecision
    safety_status: LimitedGeneralRecallSafetyStatus

    def as_dict(self) -> dict[str, object]:
        return {
            "trace_id": self.trace_id,
            "request": self.request.as_dict(),
            "source_snapshot": self.source_snapshot.as_dict(),
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "decision": self.decision.as_dict(),
            "safety_status": self.safety_status.as_dict(),
        }


@dataclass(frozen=True)
class LimitedGeneralRecallReportEntry:
    report_entry_id: str
    query: str
    candidate_count: int
    safe: bool

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def run_limited_general_recall_trial(query: str, *, max_candidates: int = 3) -> dict[str, object]:
    request = LimitedGeneralRecallTrialRequest(_stable_id("v17f-request", query, max_candidates), query, max_candidates)
    snapshot = LimitedGeneralRecallSourceSnapshot(
        _stable_id("v17f-snapshot", "candidate-context"),
        allowed_sources=("V1.5I non-rolled-back local trial records", "local static knowledge", "evaluator advisory reports as advisory only", "provider/specialist evidence packets as evidence only"),
        disallowed_sources=("raw conversation as canonical memory", "unapproved memory candidates as truth", "rejected records", "rolled-back records", "provider output as memory", "evaluator output as authority"),
    )
    candidates = _candidate_contexts(query, max_candidates)
    decision = LimitedGeneralRecallDecision(_stable_id("v17f-decision", request.request_id, len(candidates)), len(candidates), max_candidates)
    safety = LimitedGeneralRecallSafetyStatus(_stable_id("v17f-safety", request.request_id), _candidates_safe(candidates), "candidate-context only; no mutation")
    trace = LimitedGeneralRecallTrace(_stable_id("v17f-trace", request.request_id), request, snapshot, tuple(candidates), decision, safety)
    return {
        "phase": "Runtime V1.7F",
        "trace": trace.as_dict(),
        "report_entry": LimitedGeneralRecallReportEntry(_stable_id("v17f-entry", request.request_id), query, len(candidates), safety.safe).as_dict(),
        "invariant_flags": dict(RUNTIME_V17F_FLAGS),
        "final_recommendation": "PROCEED_CONTROLLED_ANSWER_SYNTHESIS",
    }


def validate_limited_general_recall_trial_safe(payload: dict[str, object]) -> bool:
    flags = payload["invariant_flags"]
    trace = payload["trace"]
    candidates = trace["candidates"]
    return (
        trace["decision"]["selected_count"] <= trace["decision"]["max_candidates"]
        and trace["decision"]["candidate_context_only"] is True
        and trace["decision"]["memory_write_performed"] is False
        and trace["decision"]["recall_mutated"] is False
        and all(candidate["candidate_context_only"] is True and candidate["authoritative"] is False and candidate["rejected_or_rolled_back"] is False for candidate in candidates)
        and flags["limited_general_recall_trial_enabled"] is True
        and flags["candidate_context_only"] is True
        and all(value is False for key, value in flags.items() if key not in {"limited_general_recall_trial_enabled", "candidate_context_only"})
    )


def _candidate_contexts(query: str, max_candidates: int) -> list[LimitedGeneralRecallCandidate]:
    routed = route_limited_general_recall(query)
    candidates: list[LimitedGeneralRecallCandidate] = []
    for raw in routed["candidates"]:
        candidates.append(
            LimitedGeneralRecallCandidate(
                candidate_id=_stable_id("v17f-candidate", raw.get("candidate_id", "")),
                source_kind=_map_source_kind(str(raw.get("source_kind", ""))),
                text=str(raw.get("text", "")),
                provenance=str(raw.get("source_reference", "")),
                rank=len(candidates) + 1,
            )
        )
    local = route_local_knowledge_answer(query)
    if local.matched and local.answer:
        candidates.append(
            LimitedGeneralRecallCandidate(
                candidate_id=_stable_id("v17f-local", local.topic_id),
                source_kind=LimitedGeneralRecallSourceKind.LOCAL_STATIC,
                text=local.answer.answer_text,
                provenance=local.answer.source_summary,
                rank=len(candidates) + 1,
            )
        )
    return candidates[:max_candidates]


def _map_source_kind(value: str) -> LimitedGeneralRecallSourceKind:
    if value == "v15i_trial_record":
        return LimitedGeneralRecallSourceKind.V15I_CANONICAL_TRIAL
    if value == "evaluator_advisory":
        return LimitedGeneralRecallSourceKind.EVALUATOR_ADVISORY
    return LimitedGeneralRecallSourceKind.LOCAL_STATIC


def _candidates_safe(candidates: list[LimitedGeneralRecallCandidate]) -> bool:
    return all(candidate.candidate_context_only and not candidate.authoritative and not candidate.rejected_or_rolled_back for candidate in candidates)


def _stable_id(prefix: str, *parts: object) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"
