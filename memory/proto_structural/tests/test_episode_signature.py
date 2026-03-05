from memory.proto_structural.episode_signature import EpisodeSignature


def test_episode_signature_is_immutable_and_hashable():
    sig = EpisodeSignature(
        length_steps=10,
        event_count=3,
        event_types=frozenset({"A", "B"}),
        region_ids=frozenset({"R1"}),
        transition_counts=(("A", "B", 2),),
    )

    # Hashable
    h1 = hash(sig)
    h2 = hash(sig)
    assert h1 == h2

    # Canonical tuple stability
    assert sig.as_canonical_tuple() == sig.as_canonical_tuple()

    # Equality semantics
    sig2 = EpisodeSignature(
        length_steps=10,
        event_count=3,
        event_types=frozenset({"B", "A"}),
        region_ids=frozenset({"R1"}),
        transition_counts=(("A", "B", 2),),
    )

    assert sig == sig2
