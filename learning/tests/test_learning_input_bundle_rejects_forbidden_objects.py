from __future__ import annotations

import pytest

from learning.inputs.learning_pipeline_input_adapter import LearningPipelineInputAdapter
from memory.semantic_activation.semantic_activation_record import SemanticActivationRecord
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.episode_signature import EpisodeSignature


class _CallableValue:
    def __call__(self):
        return 1


class _StatefulValue:
    def __init__(self):
        self.state = {"x": 1}


def test_learning_input_bundle_rejects_non_data_tag_values():
    """
    CONTRACT:
    Learning input tags must contain only inert, data-only values.
    Objects with behavior or internal mutable state are not permitted.
    """

    adapter = LearningPipelineInputAdapter()

    sem = SemanticActivationRecord(
        activations={"sem:alpha": 0.3},
        snapshot_index=1,
    )

    sig = EpisodeSignature(
        length_steps=5,
        event_count=1,
        event_types=frozenset({"close"}),
        region_ids=frozenset({"GPi"}),
        transition_counts=(),
    )

    patterns = PatternRecord(pattern_counts={sig: 1})

    # Callable value rejected
    with pytest.raises(TypeError):
        adapter.from_inspection_surface(
            replay_id="replay:test",
            semantic_activation_records=[sem],
            pattern_record=patterns,
            tags={"callable_value": _CallableValue()},
        )

    # Stateful value rejected
    with pytest.raises(TypeError):
        adapter.from_inspection_surface(
            replay_id="replay:test",
            semantic_activation_records=[sem],
            pattern_record=patterns,
            tags={"stateful_value": _StatefulValue()},
        )
