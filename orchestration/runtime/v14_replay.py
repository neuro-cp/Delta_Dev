from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from orchestration.runtime.v14_episode import EpisodeReplayStatus, EpisodeTrace
from orchestration.runtime.v14_feedback import (
    FeedbackCaptureRecord,
    FeedbackDisposition,
    FeedbackPolarity,
)
from orchestration.runtime.v14_feedback_to_pruning import PruningReviewProposal
from orchestration.runtime.v14_replay_markers import ReplayReviewMarker
from orchestration.runtime.v14_trace import ReplayEligibility


RUNTIME_V14E_INVARIANT_FLAGS: dict[str, bool] = {
    "canonical_write_enabled": False,
    "training_enabled": False,
    "pruning_enabled": False,
    "provider_calls_enabled": False,
    "scheduler_enabled": False,
    "runtime_defaults_changed": False,
    "active_replay_enabled": False,
    "live_routing_enabled": False,
    "execution_enabled": False,
}


class ReplayBatchStatus(str, Enum):
    DRAFT = "draft"
    REVIEW_READY = "review_ready"
    BLOCKED_BY_INVARIANT = "blocked_by_invariant"
    BENCHMARK_ONLY_DO_NOT_TRAIN = "benchmark_only_do_not_train"


class ReplayReviewFinding(str, Enum):
    USEFUL_SIGNAL = "useful_signal"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    SAFETY_BLOCKED = "safety_blocked"
    HUMAN_REVIEW_NEEDED = "human_review_needed"
    BENCHMARK_ONLY = "benchmark_only"
    PRUNING_REVIEW_SIGNAL = "pruning_review_signal"
    NO_ACTION = "no_action"


@dataclass(frozen=True)
class ReplayBatch:
    batch_id: str
    episode_ids: tuple[str, ...] = ()
    feedback_ids: tuple[str, ...] = ()
    replay_marker_ids: tuple[str, ...] = ()
    pruning_proposal_ids: tuple[str, ...] = ()
    status: ReplayBatchStatus = ReplayBatchStatus.DRAFT
    eligibility_notes: tuple[str, ...] = ()
    invariant_flags: dict[str, bool] = field(default_factory=lambda: dict(RUNTIME_V14E_INVARIANT_FLAGS))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: str = ""

    @property
    def item_count(self) -> int:
        return (
            len(self.episode_ids)
            + len(self.feedback_ids)
            + len(self.replay_marker_ids)
            + len(self.pruning_proposal_ids)
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "batch_id": self.batch_id,
            "episode_ids": list(self.episode_ids),
            "feedback_ids": list(self.feedback_ids),
            "replay_marker_ids": list(self.replay_marker_ids),
            "pruning_proposal_ids": list(self.pruning_proposal_ids),
            "status": self.status.value,
            "item_count": self.item_count,
            "eligibility_notes": list(self.eligibility_notes),
            "invariant_flags": dict(self.invariant_flags),
            "created_at": self.created_at,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ReplayReviewResult:
    review_id: str
    batch_id: str
    findings: tuple[ReplayReviewFinding, ...] = ()
    useful_signal_count: int = 0
    insufficient_evidence_count: int = 0
    conflicting_evidence_count: int = 0
    safety_blocked_count: int = 0
    human_review_needed: bool = False
    candidate_recommended: bool = False
    canonical_write_enabled: bool = False
    training_enabled: bool = False
    pruning_enabled: bool = False
    provider_calls_enabled: bool = False
    scheduler_enabled: bool = False
    active_replay_enabled: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rationale: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "review_id": self.review_id,
            "batch_id": self.batch_id,
            "findings": [finding.value for finding in self.findings],
            "useful_signal_count": self.useful_signal_count,
            "insufficient_evidence_count": self.insufficient_evidence_count,
            "conflicting_evidence_count": self.conflicting_evidence_count,
            "safety_blocked_count": self.safety_blocked_count,
            "human_review_needed": self.human_review_needed,
            "candidate_recommended": self.candidate_recommended,
            "canonical_write_enabled": self.canonical_write_enabled,
            "training_enabled": self.training_enabled,
            "pruning_enabled": self.pruning_enabled,
            "provider_calls_enabled": self.provider_calls_enabled,
            "scheduler_enabled": self.scheduler_enabled,
            "active_replay_enabled": self.active_replay_enabled,
            "created_at": self.created_at,
            "rationale": self.rationale,
            "notes": self.notes,
        }


def create_replay_batch(
    *,
    episodes: tuple[EpisodeTrace, ...] | list[EpisodeTrace] = (),
    feedback_records: tuple[FeedbackCaptureRecord, ...] | list[FeedbackCaptureRecord] = (),
    replay_markers: tuple[ReplayReviewMarker, ...] | list[ReplayReviewMarker] = (),
    pruning_proposals: tuple[PruningReviewProposal, ...] | list[PruningReviewProposal] = (),
    notes: str = "",
) -> ReplayBatch:
    episode_ids = tuple(_unique_sorted(episode.episode_id for episode in episodes))
    feedback_ids = tuple(_unique_sorted(record.feedback_id for record in feedback_records))
    marker_ids = tuple(_unique_sorted(marker.marker_id for marker in replay_markers))
    proposal_ids = tuple(_unique_sorted(proposal.proposal_id for proposal in pruning_proposals))
    status, eligibility_notes = _classify_batch_status(
        episodes=tuple(episodes),
        feedback_records=tuple(feedback_records),
        replay_markers=tuple(replay_markers),
        pruning_proposals=tuple(pruning_proposals),
    )
    return ReplayBatch(
        batch_id=_stable_id("replay-batch", (*episode_ids, *feedback_ids, *marker_ids, *proposal_ids)),
        episode_ids=episode_ids,
        feedback_ids=feedback_ids,
        replay_marker_ids=marker_ids,
        pruning_proposal_ids=proposal_ids,
        status=status,
        eligibility_notes=eligibility_notes,
        notes=notes or "batch is review-only; replay is not executed",
    )


def review_replay_batch(
    batch: ReplayBatch,
    *,
    episodes: tuple[EpisodeTrace, ...] | list[EpisodeTrace] = (),
    feedback_records: tuple[FeedbackCaptureRecord, ...] | list[FeedbackCaptureRecord] = (),
    replay_markers: tuple[ReplayReviewMarker, ...] | list[ReplayReviewMarker] = (),
    pruning_proposals: tuple[PruningReviewProposal, ...] | list[PruningReviewProposal] = (),
) -> ReplayReviewResult:
    findings = _collect_findings(
        batch=batch,
        episodes=tuple(episodes),
        feedback_records=tuple(feedback_records),
        replay_markers=tuple(replay_markers),
        pruning_proposals=tuple(pruning_proposals),
    )
    useful_count = findings.count(ReplayReviewFinding.USEFUL_SIGNAL) + findings.count(
        ReplayReviewFinding.PRUNING_REVIEW_SIGNAL
    )
    insufficient_count = findings.count(ReplayReviewFinding.INSUFFICIENT_EVIDENCE)
    conflicting_count = findings.count(ReplayReviewFinding.CONFLICTING_EVIDENCE)
    safety_count = findings.count(ReplayReviewFinding.SAFETY_BLOCKED)
    human_review = ReplayReviewFinding.HUMAN_REVIEW_NEEDED in findings or safety_count > 0
    candidate_recommended = (
        batch.status == ReplayBatchStatus.REVIEW_READY
        and useful_count > 0
        and safety_count == 0
        and ReplayReviewFinding.BENCHMARK_ONLY not in findings
    )
    return ReplayReviewResult(
        review_id=_stable_id("replay-review", (batch.batch_id, *[finding.value for finding in findings])),
        batch_id=batch.batch_id,
        findings=findings,
        useful_signal_count=useful_count,
        insufficient_evidence_count=insufficient_count,
        conflicting_evidence_count=conflicting_count,
        safety_blocked_count=safety_count,
        human_review_needed=human_review,
        candidate_recommended=candidate_recommended,
        rationale=_review_rationale(findings, candidate_recommended),
        notes="review result only; no consolidation, training, provider call, or memory mutation performed",
    )


def validate_replay_batch_non_mutating(batch: ReplayBatch) -> bool:
    return (
        all(value is False for value in batch.invariant_flags.values())
        and batch.status != ReplayBatchStatus.BLOCKED_BY_INVARIANT
    )


def validate_replay_review_non_mutating(result: ReplayReviewResult) -> bool:
    return not any(
        (
            result.canonical_write_enabled,
            result.training_enabled,
            result.pruning_enabled,
            result.provider_calls_enabled,
            result.scheduler_enabled,
            result.active_replay_enabled,
        )
    )


def _classify_batch_status(
    *,
    episodes: tuple[EpisodeTrace, ...],
    feedback_records: tuple[FeedbackCaptureRecord, ...],
    replay_markers: tuple[ReplayReviewMarker, ...],
    pruning_proposals: tuple[PruningReviewProposal, ...],
) -> tuple[ReplayBatchStatus, tuple[str, ...]]:
    notes: list[str] = []
    all_benchmark = bool(episodes or feedback_records or replay_markers) and all(
        (
            *(episode.benchmark_only for episode in episodes),
            *(record.benchmark_only for record in feedback_records),
            *(marker.eligibility == ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN for marker in replay_markers),
        )
    )
    if all_benchmark:
        return ReplayBatchStatus.BENCHMARK_ONLY_DO_NOT_TRAIN, ("benchmark-only material must not train",)
    if any(value is True for value in RUNTIME_V14E_INVARIANT_FLAGS.values()):
        return ReplayBatchStatus.BLOCKED_BY_INVARIANT, ("a forbidden V1.4E capability flag is enabled",)
    reviewable = any(
        (
            *(episode.replay_status in {EpisodeReplayStatus.REPLAY_CANDIDATE, EpisodeReplayStatus.REQUIRES_HUMAN_REVIEW} for episode in episodes),
            *(record.proposed_disposition in {
                FeedbackDisposition.ELIGIBLE_FOR_REPLAY,
                FeedbackDisposition.PRUNING_REVIEW_CANDIDATE,
                FeedbackDisposition.REQUIRES_HUMAN_REVIEW,
            } for record in feedback_records),
            *(marker.eligibility in {
                ReplayEligibility.ELIGIBLE_FOR_REVIEW,
                ReplayEligibility.ELIGIBLE_FOR_REPLAY,
                ReplayEligibility.REQUIRES_HUMAN_REVIEW,
            } for marker in replay_markers),
            bool(pruning_proposals),
        )
    )
    if reviewable:
        notes.append("contains reviewable signals")
        return ReplayBatchStatus.REVIEW_READY, tuple(notes)
    return ReplayBatchStatus.DRAFT, ("no reviewable signals found",)


def _collect_findings(
    *,
    batch: ReplayBatch,
    episodes: tuple[EpisodeTrace, ...],
    feedback_records: tuple[FeedbackCaptureRecord, ...],
    replay_markers: tuple[ReplayReviewMarker, ...],
    pruning_proposals: tuple[PruningReviewProposal, ...],
) -> tuple[ReplayReviewFinding, ...]:
    findings: list[ReplayReviewFinding] = []
    if batch.status == ReplayBatchStatus.BENCHMARK_ONLY_DO_NOT_TRAIN:
        findings.append(ReplayReviewFinding.BENCHMARK_ONLY)
    for episode in episodes:
        if episode.benchmark_only:
            findings.append(ReplayReviewFinding.BENCHMARK_ONLY)
        if episode.human_review_required:
            findings.append(ReplayReviewFinding.HUMAN_REVIEW_NEEDED)
        if episode.replay_status == EpisodeReplayStatus.REQUIRES_HUMAN_REVIEW:
            findings.append(ReplayReviewFinding.SAFETY_BLOCKED)
        elif episode.replay_status == EpisodeReplayStatus.REPLAY_CANDIDATE:
            findings.append(ReplayReviewFinding.USEFUL_SIGNAL)
    for record in feedback_records:
        if record.benchmark_only:
            findings.append(ReplayReviewFinding.BENCHMARK_ONLY)
        if record.human_review_required:
            findings.append(ReplayReviewFinding.HUMAN_REVIEW_NEEDED)
        if record.polarity == FeedbackPolarity.ASKS_FOR_MORE_EVIDENCE:
            findings.append(ReplayReviewFinding.INSUFFICIENT_EVIDENCE)
        elif record.polarity == FeedbackPolarity.FLAGS_SAFETY_RISK:
            findings.append(ReplayReviewFinding.SAFETY_BLOCKED)
        elif record.polarity in {FeedbackPolarity.CORRECTS, FeedbackPolarity.REJECTS}:
            findings.append(ReplayReviewFinding.CONFLICTING_EVIDENCE)
        elif record.proposed_disposition == FeedbackDisposition.PRUNING_REVIEW_CANDIDATE:
            findings.append(ReplayReviewFinding.PRUNING_REVIEW_SIGNAL)
    for marker in replay_markers:
        if marker.eligibility == ReplayEligibility.BENCHMARK_ONLY_DO_NOT_TRAIN:
            findings.append(ReplayReviewFinding.BENCHMARK_ONLY)
        elif marker.eligibility == ReplayEligibility.REQUIRES_HUMAN_REVIEW:
            findings.append(ReplayReviewFinding.HUMAN_REVIEW_NEEDED)
        elif marker.eligibility in {ReplayEligibility.ELIGIBLE_FOR_REVIEW, ReplayEligibility.ELIGIBLE_FOR_REPLAY}:
            findings.append(ReplayReviewFinding.USEFUL_SIGNAL)
    if pruning_proposals:
        findings.append(ReplayReviewFinding.PRUNING_REVIEW_SIGNAL)
    if not findings:
        findings.append(ReplayReviewFinding.NO_ACTION)
    return tuple(_dedupe_preserve_order(findings))


def _review_rationale(findings: tuple[ReplayReviewFinding, ...], candidate_recommended: bool) -> str:
    if candidate_recommended:
        return "Replay found reviewable material that may become a consolidation candidate, but no consolidation is applied."
    if ReplayReviewFinding.BENCHMARK_ONLY in findings:
        return "Replay material is benchmark-only and must not be used for training."
    if ReplayReviewFinding.SAFETY_BLOCKED in findings:
        return "Replay material requires safety or human review before any future consolidation."
    return "Replay did not produce a consolidation candidate."


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    payload = "|".join(part for part in parts if part)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16] if payload else "empty"
    return f"{prefix}-{digest}"


def _unique_sorted(values: object) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values if str(value)}))


def _dedupe_preserve_order(values: list[ReplayReviewFinding]) -> list[ReplayReviewFinding]:
    seen: set[ReplayReviewFinding] = set()
    output: list[ReplayReviewFinding] = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output
