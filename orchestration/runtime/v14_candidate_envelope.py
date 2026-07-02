from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_lanes import ConceptLaneState
from orchestration.runtime.v14_pruning import PruningRecord
from orchestration.runtime.v14_signals import SemanticSignalSet, empty_signal_set


class CandidateState(str, Enum):
    GENERATED = "generated"
    VALIDATED = "validated"
    QUEUED_FOR_REPLAY = "queued_for_replay"
    REPLAY_COMPLETED = "replay_completed"
    ELIGIBLE_FOR_REVIEW = "eligible_for_review"
    AUTHORIZED = "authorized"
    VETOED = "vetoed"
    ARCHIVED = "archived"


ALLOWED_TRANSITIONS: dict[CandidateState, set[CandidateState]] = {
    CandidateState.GENERATED: {CandidateState.VALIDATED, CandidateState.VETOED, CandidateState.ARCHIVED},
    CandidateState.VALIDATED: {
        CandidateState.QUEUED_FOR_REPLAY,
        CandidateState.ELIGIBLE_FOR_REVIEW,
        CandidateState.VETOED,
        CandidateState.ARCHIVED,
    },
    CandidateState.QUEUED_FOR_REPLAY: {
        CandidateState.REPLAY_COMPLETED,
        CandidateState.VETOED,
        CandidateState.ARCHIVED,
    },
    CandidateState.REPLAY_COMPLETED: {
        CandidateState.ELIGIBLE_FOR_REVIEW,
        CandidateState.VETOED,
        CandidateState.ARCHIVED,
    },
    CandidateState.ELIGIBLE_FOR_REVIEW: {
        CandidateState.AUTHORIZED,
        CandidateState.VETOED,
        CandidateState.ARCHIVED,
    },
    CandidateState.AUTHORIZED: {CandidateState.ARCHIVED},
    CandidateState.VETOED: {CandidateState.ARCHIVED},
    CandidateState.ARCHIVED: set(),
}


@dataclass(frozen=True)
class CandidateProvenance:
    source: str
    source_id: str = ""
    report_path: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "report_path": self.report_path,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CandidateConfidence:
    value: float = 0.0
    evidence_support: float = 0.0
    uncertainty: float = 1.0
    rationale: str = ""

    def normalized_value(self) -> float:
        return max(0.0, min(1.0, float(self.value)))

    def as_dict(self) -> dict[str, object]:
        return {
            "value": self.normalized_value(),
            "evidence_support": max(0.0, min(1.0, float(self.evidence_support))),
            "uncertainty": max(0.0, min(1.0, float(self.uncertainty))),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class CandidateDecisionTrace:
    decision: str
    reason: str
    actor: str = "runtime_v14_scaffold"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "actor": self.actor,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CandidateEnvelope:
    envelope_id: str
    candidate_type: str
    payload: dict[str, object]
    provenance: CandidateProvenance
    confidence: CandidateConfidence = field(default_factory=CandidateConfidence)
    decision_trace: tuple[CandidateDecisionTrace, ...] = ()
    state: CandidateState = CandidateState.GENERATED
    signal_set: SemanticSignalSet = field(default_factory=empty_signal_set)
    lane_state: ConceptLaneState | None = None
    pruning_records: tuple[PruningRecord, ...] = ()
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def can_transition_to(self, target: CandidateState) -> bool:
        return validate_transition(self.state, target)

    def transition(self, target: CandidateState, *, reason: str = "") -> "CandidateEnvelope":
        return transition_candidate(self, target, reason=reason)

    def with_pruning_record(self, record: PruningRecord) -> "CandidateEnvelope":
        return replace(
            self,
            pruning_records=(*self.pruning_records, record),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "envelope_id": self.envelope_id,
            "candidate_type": self.candidate_type,
            "payload": self.payload,
            "provenance": self.provenance.as_dict(),
            "confidence": self.confidence.as_dict(),
            "decision_trace": [trace.as_dict() for trace in self.decision_trace],
            "state": self.state.value,
            "signal_set": self.signal_set.as_dict(),
            "lane_state": self.lane_state.as_dict() if self.lane_state else None,
            "pruning_records": [record.as_dict() for record in self.pruning_records],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def create_candidate_envelope(
    *,
    envelope_id: str,
    candidate_type: str,
    payload: dict[str, object],
    provenance: CandidateProvenance | None = None,
    confidence: CandidateConfidence | None = None,
) -> CandidateEnvelope:
    return CandidateEnvelope(
        envelope_id=envelope_id,
        candidate_type=candidate_type,
        payload=payload,
        provenance=provenance or CandidateProvenance(source="runtime_v14_scaffold"),
        confidence=confidence or CandidateConfidence(),
        decision_trace=(CandidateDecisionTrace(decision="created", reason="candidate envelope created"),),
    )


def validate_transition(current: CandidateState, target: CandidateState) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def transition_candidate(
    envelope: CandidateEnvelope,
    target: CandidateState,
    *,
    reason: str = "",
) -> CandidateEnvelope:
    if not validate_transition(envelope.state, target):
        raise ValueError(f"Invalid CandidateEnvelope transition: {envelope.state.value} -> {target.value}")
    trace = CandidateDecisionTrace(
        decision=f"{envelope.state.value}->{target.value}",
        reason=reason or "valid lifecycle transition",
    )
    return replace(
        envelope,
        state=target,
        decision_trace=(*envelope.decision_trace, trace),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


def archive_candidate(envelope: CandidateEnvelope, *, reason: str = "archived") -> CandidateEnvelope:
    if envelope.state == CandidateState.ARCHIVED:
        return envelope
    return transition_candidate(envelope, CandidateState.ARCHIVED, reason=reason)


def create_generated_envelope(
    *,
    envelope_id: str,
    candidate_type: str,
    payload: dict[str, object],
    provenance: tuple[str, ...] = (),
    confidence: float = 0.0,
) -> CandidateEnvelope:
    source = provenance[0] if provenance else "runtime_v14_scaffold"
    return create_candidate_envelope(
        envelope_id=envelope_id,
        candidate_type=candidate_type,
        payload=payload,
        provenance=CandidateProvenance(source=source, notes="; ".join(provenance[1:])),
        confidence=CandidateConfidence(value=confidence),
    )


CandidateEnvelopeState = CandidateState
