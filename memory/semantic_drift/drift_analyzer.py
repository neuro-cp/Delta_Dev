from __future__ import annotations

from collections import defaultdict
from typing import List, Dict, Iterable, Tuple

from memory.semantic.registry import SemanticRegistry
from memory.semantic.records import SemanticRecord
from memory.semantic_drift.drift_record import DriftRecord


class DriftAnalyzer:
    """
    Offline semantic drift analyzer.

    Consumes SemanticRegistry snapshots and produces DriftRecords.
    This analyzer is strictly descriptive:
    - no runtime access
    - no mutation
    - no authority
    """

    def __init__(
        self,
        registry: SemanticRegistry,
        *,
        policy_version: str = "v0",
        schema_version: str = "v0",
    ) -> None:
        self._registry = registry
        self._policy_version = policy_version
        self._schema_version = schema_version

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def analyze(
        self,
        *,
        window_start_episode: int,
        window_end_episode: int,
    ) -> List[DriftRecord]:
        """
        Analyze semantic drift over a closed episode window.

        The window is inclusive.
        """
        records = self._records_in_window(
            window_start_episode,
            window_end_episode,
        )

        grouped = self._group_by_type(records)

        drift_records: List[DriftRecord] = []

        for semantic_type, group in grouped.items():
            drift_records.append(
                self._analyze_group(
                    semantic_type=semantic_type,
                    records=group,
                    window_start_episode=window_start_episode,
                    window_end_episode=window_end_episode,
                )
            )

        return drift_records

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _records_in_window(
        self,
        start_ep: int,
        end_ep: int,
    ) -> List[SemanticRecord]:
        """
        Select semantic records whose episode_ids intersect the window.
        """
        selected: List[SemanticRecord] = []

        for record in self._registry.records:
            episode_ids = record.provenance.episode_ids
            if any(start_ep <= ep_id <= end_ep for ep_id in episode_ids):
                selected.append(record)


        return selected

    @staticmethod
    def _group_by_type(
        records: Iterable[SemanticRecord],
    ) -> Dict[str, List[SemanticRecord]]:
        grouped: Dict[str, List[SemanticRecord]] = defaultdict(list)
        for r in records:
            grouped[r.pattern_type].append(r)
        return grouped

    def _analyze_group(
        self,
        *,
        semantic_type: str,
        records: List[SemanticRecord],
        window_start_episode: int,
        window_end_episode: int,
    ) -> DriftRecord:
        episode_ids = sorted(
            {ep for r in records for ep in r.provenance.episode_ids}
        )

        total_occurrences = len(records)
        unique_episode_count = len(episode_ids)

        first_seen = min(episode_ids)
        last_seen = max(episode_ids)
        persistence_span = last_seen - first_seen

        is_novel = first_seen >= window_start_episode
        is_recurrent = unique_episode_count > 1
        is_persistent = persistence_span > 0

        window_size = max(1, window_end_episode - window_start_episode + 1)

        frequency_per_episode = total_occurrences / window_size
        density = unique_episode_count / window_size

        return DriftRecord(
            semantic_type=semantic_type,
            window_start_episode=window_start_episode,
            window_end_episode=window_end_episode,
            total_occurrences=total_occurrences,
            unique_episode_count=unique_episode_count,
            first_seen_episode=first_seen,
            last_seen_episode=last_seen,
            persistence_span=persistence_span,
            is_novel=is_novel,
            is_recurrent=is_recurrent,
            is_persistent=is_persistent,
            frequency_per_episode=frequency_per_episode,
            density=density,
            policy_version=self._policy_version,
            schema_version=self._schema_version,
            tags={},
        )
