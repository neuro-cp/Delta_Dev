from memory.proto_structural.episode_signature import EpisodeSignature
from learning.session.proposal_generators.structural_pattern_proposal_generator import (
    StructuralPatternProposalGenerator,
)


def _make_signature():
    return EpisodeSignature(
        length_steps=10,
        event_count=3,
        event_types=frozenset({"a", "b"}),
        region_ids=frozenset({"stn"}),
        transition_counts=(("a", "b", 2),),
    )


def test_structural_generator_emits_proposal_when_eligible():
    sig = _make_signature()

    pattern_counts = {sig: 3}

    gen = StructuralPatternProposalGenerator()

    proposals = gen.generate(
        replay_id="r1",
        pattern_counts=pattern_counts,
    )

    assert len(proposals) == 1
    assert proposals[0].bounded is True
    assert "structural" in proposals[0].audit_tags


def test_structural_generator_rejects_insufficient_evidence():
    sig = _make_signature()

    pattern_counts = {sig: 1}

    gen = StructuralPatternProposalGenerator()

    proposals = gen.generate(
        replay_id="r1",
        pattern_counts=pattern_counts,
    )

    assert proposals == []