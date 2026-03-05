from memory.proto_structural.episode_signature import EpisodeSignature
from memory.proto_structural.pattern_record import PatternRecord
from memory.proto_structural.pattern_statistics import PatternStatisticsBuilder
from memory.proto_learning.structural_eligibility.structural_eligibility_engine import StructuralEligibilityEngine

def _make_signature() -> EpisodeSignature:
    return EpisodeSignature(
        length_steps=10,
        event_count=3,
        event_types=frozenset({"a", "b"}),
        region_ids=frozenset({"stn"}),
        transition_counts=(("a","b",2),),
    )

def test_structural_eligibility_basic_threshold():
    sig = _make_signature()
    record = PatternRecord(pattern_counts={sig: 3})
    stats = PatternStatisticsBuilder().build(record=record)

    engine = StructuralEligibilityEngine(
        min_occurrences=3,
        min_relative_frequency=1.0,
    )

    candidates = engine.evaluate(stats=stats)
    assert len(candidates) == 1
    assert candidates[0].occurrences == 3

def test_structural_eligibility_rejects_low_frequency():
    sig1 = _make_signature()
    sig2 = EpisodeSignature(
        length_steps=5,
        event_count=2,
        event_types=frozenset({"x"}),
        region_ids=frozenset({"pfc"}),
        transition_counts=(("x","x",1),),
    )

    record = PatternRecord(pattern_counts={sig1: 3, sig2: 3})
    stats = PatternStatisticsBuilder().build(record=record)

    engine = StructuralEligibilityEngine(
        min_occurrences=3,
        min_relative_frequency=0.6,
    )

    candidates = engine.evaluate(stats=stats)
    assert len(candidates) == 0
