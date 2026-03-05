from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Iterable, Optional

from memory.episodic.episode_replay import EpisodeReplay
from memory.episodic.episode_structure import Episode
from memory.episodic.episode_trace import EpisodeTraceRecord
from memory.episodic.signal_snapshot import SignalSnapshot


# ============================================================
# Narrative event (purely descriptive)
# ============================================================

@dataclass(frozen=True)
class NarrativeEvent:
    """
    Human-readable description of a single episodic event.

    This object is:
    - read-only
    - offline
    - descriptive only
    - non-semantic
    """

    episode_id: int
    step: int
    kind: str           # "start", "signal", "decision", "close", "info"
    message: str
    payload: Dict[str, Any]


# ============================================================
# Episode narrator
# ============================================================

class EpisodeNarrator:
    """
    Offline episodic narrator.

    Responsibilities:
    - Consume EpisodeReplay + EpisodeTrace
    - Optionally consume SignalSnapshots
    - Produce a temporal narrative of what occurred
    - Describe dynamics WITHOUT interpretation or intent

    Non-responsibilities:
    - No learning
    - No inference
    - No runtime access
    - No semantic abstraction
    """

    def narrate(
        self,
        replay: EpisodeReplay,
        *,
        signals: Optional[List[SignalSnapshot]] = None,
    ) -> List[NarrativeEvent]:
        """
        Produce a narrative for all closed episodes in the replay.

        Salience / value / urgency signals are treated as an
        INDEPENDENT observational timeline and aligned by step.
        """
        narrative: List[NarrativeEvent] = []

        signal_index = self._index_signals(signals)

        for episode, episode_records, salience_records in replay.replay():
            narrative.extend(
                self._narrate_episode(
                    episode=episode,
                    records=episode_records,
                    signal_index=signal_index,
                )
            )

        return narrative

    # --------------------------------------------------
    # Episode-level narration
    # --------------------------------------------------

    def _narrate_episode(
        self,
        *,
        episode: Episode,
        records: Iterable[EpisodeTraceRecord],
        signal_index: Dict[int, SignalSnapshot],
    ) -> List[NarrativeEvent]:
        events: List[NarrativeEvent] = []

        end_step = episode.end_step

        # --------------------------------------------------
        # Episode header
        # --------------------------------------------------
        events.append(
            NarrativeEvent(
                episode_id=episode.episode_id,
                step=episode.start_step,
                kind="start",
                message=f"Episode {episode.episode_id} started at step {episode.start_step}.",
                payload={
                    "start_step": episode.start_step,
                    "tags": dict(episode.tags),
                },
            )
        )

        # --------------------------------------------------
        # Signal annotations (independent timeline)
        # --------------------------------------------------
        for step, snapshot in signal_index.items():
            if not snapshot.is_nonbaseline():
                continue

            if step < episode.start_step:
                continue

            if end_step is not None and step > end_step:
                continue

            events.append(
                NarrativeEvent(
                    episode_id=episode.episode_id,
                    step=step,
                    kind="signal",
                    message=self._format_signal(snapshot),
                    payload=snapshot.as_dict(),
                )
            )

        # --------------------------------------------------
        # Trace-driven narration
        # --------------------------------------------------
        for r in records:
            if r.event == "decision":
                events.append(
                    NarrativeEvent(
                        episode_id=episode.episode_id,
                        step=r.step,
                        kind="decision",
                        message=self._format_decision(r),
                        payload=dict(r.payload),
                    )
                )

            elif r.event == "close":
                events.append(
                    NarrativeEvent(
                        episode_id=episode.episode_id,
                        step=r.step,
                        kind="close",
                        message=self._format_close(episode, r),
                        payload=dict(r.payload),
                    )
                )

        # --------------------------------------------------
        # Post-episode summary
        # --------------------------------------------------
        summary_step = end_step if end_step is not None else episode.start_step

        events.append(
            NarrativeEvent(
                episode_id=episode.episode_id,
                step=summary_step,
                kind="info",
                message=self._format_summary(episode),
                payload={
                    "decision_count": episode.decision_count,
                    "duration_steps": episode.duration_steps,
                    "winner": episode.winner,
                    "confidence": episode.confidence,
                },
            )
        )

        # --------------------------------------------------
        # Temporal ordering (single authoritative sort)
        # --------------------------------------------------
        events.sort(key=lambda e: e.step)

        return events

    # --------------------------------------------------
    # Signal helpers (descriptive only)
    # --------------------------------------------------

    def _index_signals(
        self,
        signals: Optional[List[SignalSnapshot]],
    ) -> Dict[int, SignalSnapshot]:
        """
        Index signals by timestep for O(1) lookup.
        """
        if not signals:
            return {}

        return {s.step: s for s in signals}

    def _format_signal(self, snapshot: SignalSnapshot) -> str:
        parts: List[str] = []

        if snapshot.salience not in (None, 0.0):
            parts.append(f"salience={snapshot.salience:.3f}")
        if snapshot.value not in (None, 0.0):
            parts.append(f"value={snapshot.value:.3f}")
        if snapshot.urgency not in (None, 0.0):
            parts.append(f"urgency={snapshot.urgency:.3f}")

        joined = ", ".join(parts)
        return f"Modulatory signals active: {joined}."

    # --------------------------------------------------
    # Formatting helpers (descriptive only)
    # --------------------------------------------------

    def _format_decision(self, record: EpisodeTraceRecord) -> str:
        winner = record.payload.get("winner")
        confidence = record.payload.get("confidence")

        if winner is None:
            return f"Decision event at step {record.step} (no winner recorded)."

        if confidence is not None:
            return (
                f"Decision at step {record.step}: "
                f"winner={winner}, confidence={confidence:.3f}."
            )

        return f"Decision at step {record.step}: winner={winner}."

    def _format_close(self, episode: Episode, record: EpisodeTraceRecord) -> str:
        reason = record.payload.get("reason", "unspecified")
        return (
            f"Episode {episode.episode_id} closed at step {record.step} "
            f"(reason={reason})."
        )

    def _format_summary(self, episode: Episode) -> str:
        if episode.decision_count == 0:
            return (
                f"Episode {episode.episode_id} ended without a decision "
                f"after {episode.duration_steps} steps."
            )

        return (
            f"Episode {episode.episode_id} ended with "
            f"{episode.decision_count} decision(s); "
            f"winner={episode.winner}, confidence={episode.confidence}."
        )
