from __future__ import annotations

"""
Run observed learning in a simple offline batch.

This is a SCRIPT-STYLE utility, not a framework component.

CONTRACT:
- Does NOT invoke or modify learning internals
- Uses existing adapters, diffing, inspection, aggregation
- Purely observational
- Safe to delete without affecting the system
"""

from typing import List

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from learning.execution.learning_execution_observer import observe_learning_execution
from learning.diffing.learning_bundle_diff_aggregator import aggregate_learning_bundle_diffs
from learning.inspection.diff_aggregate_inspection_builder import (
    build_diff_aggregate_inspection_view,
)

from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


def run_observed_learning_batch() -> None:
    adapter = LearningPipelineInputAdapter()

    # --------------------------------------------------
    # Fixed proto-structural context (held constant)
    # --------------------------------------------------
    sig = EpisodeSignature(
        length_steps=5,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"TRN"}),
        transition_counts=(),
    )
    patterns = PatternRecord(pattern_counts={sig: 1})

    # --------------------------------------------------
    # Semantic input variations (the only changing signal)
    # --------------------------------------------------
    semantic_runs = [
        {"sem:a": 0.1},
        {"sem:a": 0.2},
        {"sem:a": 0.2, "sem:b": 0.1},
        {"sem:b": 0.3},
        {"sem:a": 0.1},
    ]

    execution_results = []
    diffs = []

    # --------------------------------------------------
    # Execute observed runs
    # --------------------------------------------------
    for i in range(len(semantic_runs) - 1):
        before = SemanticActivationRecord(
            activations=semantic_runs[i],
            snapshot_index=i,
        )
        after = SemanticActivationRecord(
            activations=semantic_runs[i + 1],
            snapshot_index=i + 1,
        )

        bundle_before = adapter.from_inspection_surface(
            replay_id="replay:batch",
            semantic_activation_records=[before],
            pattern_record=patterns,
        )

        bundle_after = adapter.from_inspection_surface(
            replay_id="replay:batch",
            semantic_activation_records=[after],
            pattern_record=patterns,
        )

        result = observe_learning_execution(
            input_bundle_before=bundle_before,
            input_bundle_after=bundle_after,
        )

        execution_results.append(result)
        diffs.append(result.diff)

    # --------------------------------------------------
    # Aggregate observations across runs
    # --------------------------------------------------
    aggregate = aggregate_learning_bundle_diffs(diffs)
    inspection_view = build_diff_aggregate_inspection_view(aggregate)

    # --------------------------------------------------
    # Emit human-readable output (stdout only)
    # --------------------------------------------------
    print("\n=== OBSERVED LEARNING BATCH SUMMARY ===")
    print(f"Total transitions observed: {inspection_view.total_diffs}")
    print("\nSemantic additions:")
    for k, v in inspection_view.semantic_term_add_counts.items():
        print(f"  {k}: {v}")

    print("\nSemantic removals:")
    for k, v in inspection_view.semantic_term_remove_counts.items():
        print(f"  {k}: {v}")

    print("\nStructural additions:")
    for k, v in inspection_view.structural_signature_add_counts.items():
        print(f"  {k}: {v}")

    print("\nStructural removals:")
    for k, v in inspection_view.structural_signature_remove_counts.items():
        print(f"  {k}: {v}")

    print("\n=== END SUMMARY ===\n")


if __name__ == "__main__":
    run_observed_learning_batch()
