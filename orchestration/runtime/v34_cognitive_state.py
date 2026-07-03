"""Runtime ARC I V3.4 unified cognitive state snapshot."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ExperienceState:
    current_input: str = ""
    captured: bool = False


@dataclass(frozen=True)
class MemoryState:
    candidate_context_only: bool = True
    memory_mutation_performed: bool = False


@dataclass(frozen=True)
class EvidenceState:
    evidence_count: int = 0
    authoritative: bool = False


@dataclass(frozen=True)
class ReasoningState:
    explanation_available: bool = True
    provider_required: bool = False


@dataclass(frozen=True)
class ReviewState:
    requires_review: bool = False
    admin_approved: bool = False


@dataclass(frozen=True)
class LearningState:
    opportunities: int = 0
    proposals: int = 0
    integration_write_performed: bool = False


@dataclass(frozen=True)
class RuntimeState:
    experience: ExperienceState
    memory: MemoryState
    evidence: EvidenceState
    reasoning: ReasoningState
    review: ReviewState
    learning: LearningState
    model_b_default_changed: bool = False
    hyb1_promoted: bool = False
    training_performed: bool = False
    provider_call_performed: bool = False
    scheduler_started: bool = False
    action_execution_performed: bool = False

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_runtime_state_snapshot(query: str = "") -> RuntimeState:
    return RuntimeState(
        experience=ExperienceState(current_input=query, captured=bool(query)),
        memory=MemoryState(),
        evidence=EvidenceState(evidence_count=1 if query else 0),
        reasoning=ReasoningState(),
        review=ReviewState(requires_review="learn" in query.lower()),
        learning=LearningState(opportunities=1 if "learn" in query.lower() else 0),
    )
