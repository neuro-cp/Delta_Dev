from __future__ import annotations

from collections import Counter
from typing import List

from memory.consolidation.episode_consolidator import ConsolidationRecord
from memory.semantic.builder import BaseSemanticBuilder
from memory.semantic.records import (
    SemanticRecord,
    SemanticProvenance,
    SemanticTemporalScope,
    SemanticStatistics,
    SemanticStability,
)


class FrequencySemanticBuilder(BaseSemanticBuilder):
    """
    Frequency-only semantic builder.

    Produces semantic records describing how often
    structurally defined episode properties occur.

    This builder:
    - does NOT infer causality
    - does NOT encode order
    - does NOT bias behavior
    """

    def _build_impl(
        self,
        records: List[ConsolidationRecord],
    ) -> List[SemanticRecord]:
        if not records:
            return []

        total = len(records)

        # --- Structural predicates (explicit and limited) ---

        ###pattern_type="frequency" → structural_frequency###
        
        predicates = {
            "ended_by_decision": lambda r: r.ended_by_decision,
            "silent_episode": lambda r: r.decision_count == 0,
            "multi_decision_episode": lambda r: r.decision_count > 1,
        }

        counts = Counter()
        for r in records:
            for name, fn in predicates.items():
                if fn(r):
                    counts[name] += 1

        semantics: List[SemanticRecord] = []

        first_step = min(r.start_step for r in records)
        last_step = max(r.end_step or r.start_step for r in records)

        for name, count in counts.items():
            frequency = count / total

            semantics.append(
                SemanticRecord(
                    semantic_id=f"frequency::{name}",
                    policy_version=self.policy_version,
                    schema_version=self.schema_version,
                    provenance=SemanticProvenance(
                        episode_ids=[r.episode_id for r in records],
                        sample_size=total,
                    ),
                    temporal_scope=SemanticTemporalScope(
                        first_observed_step=first_step,
                        last_observed_step=last_step,
                        observation_window=last_step - first_step,
                    ),
                    pattern_type="frequency",
                    pattern_descriptor=name,
                    statistics=SemanticStatistics(
                        count=count,
                        frequency=frequency,
                    ),
                    stability=SemanticStability(
                        support=frequency,
                    ),
                    tags={"semantic_type": "frequency"},
                )
            )

        return semantics
