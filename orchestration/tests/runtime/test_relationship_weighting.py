from __future__ import annotations

from memory.relationships import RelationshipStore


def test_relationship_strengthening_appends_weight_revision(tmp_path):
    store = RelationshipStore(tmp_path / "relationships.jsonl")
    original = store.add(
        source_id="memory-a",
        target_id="memory-b",
        relationship_type="temporal_sequence",
        confidence=0.4,
        evidence="first observation",
    )

    strengthened = store.strengthen(
        original,
        evidence="repeated observation",
        amount=0.2,
        metadata={"cycle_id": "cycle-2"},
    )

    assert strengthened.relationship_id == original.relationship_id
    assert strengthened.weight == 0.6
    assert strengthened.confidence == 0.6
    assert strengthened.reinforcement_count == 2
    assert strengthened.metadata["previous_weight"] == 0.4
    assert len(store.all()) == 2
    assert store.latest() == [strengthened]


def test_find_equivalent_and_for_memory_use_latest_relationships(tmp_path):
    store = RelationshipStore(tmp_path / "relationships.jsonl")
    original = store.add(
        source_id="memory-a",
        target_id="memory-b",
        relationship_type="similarity",
        confidence=0.3,
    )
    strengthened = store.strengthen(
        original,
        evidence="same pattern repeated",
        amount=0.1,
    )

    assert (
        store.find_equivalent(
            source_id="memory-a",
            target_id="memory-b",
            relationship_type="similarity",
        )
        == strengthened
    )
    assert store.for_memory("memory-a") == [strengthened]
