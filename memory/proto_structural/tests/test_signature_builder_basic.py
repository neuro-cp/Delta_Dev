# memory/proto_structural/tests/test_signature_builder_basic.py

from memory.proto_structural.signature_builder import EpisodeSignatureBuilder


def test_signature_builder_builds_structural_signature():
    builder = EpisodeSignatureBuilder()

    sig = builder.build(
        length_steps=5,
        events=["X", "Y", "X"],
        regions=["R1", "R2"],
        transitions=[("X", "Y"), ("Y", "X"), ("X", "Y")],
    )

    assert sig.length_steps == 5
    assert sig.event_count == 3
    assert sig.event_types == frozenset({"X", "Y"})
    assert sig.region_ids == frozenset({"R1", "R2"})

    # Transition counts are structural, not ordered
    assert ("X", "Y", 2) in sig.transition_counts
    assert ("Y", "X", 1) in sig.transition_counts
