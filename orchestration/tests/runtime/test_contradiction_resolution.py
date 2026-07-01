from __future__ import annotations

from knowledge import ContradictionEngine
from knowledge.contradiction_record import ContradictionRecord


def test_contradiction_resolution_appends_without_deleting_claims(tmp_path):
    engine = ContradictionEngine(tmp_path / "contradictions.jsonl")
    contradiction = ContradictionRecord(
        contradiction_id="c1",
        created_at="2026-06-30T00:00:00+00:00",
        claim_a_id="claim-a",
        claim_b_id="claim-b",
        reason="claims conflict",
        severity=0.7,
    )
    engine.add_all([contradiction])

    resolved = engine.resolve(
        contradiction,
        resolution="claim-a supported, claim-b remains preserved as superseded",
        evidence_ids=["m1", "m2"],
        rationale="later observations support claim-a",
        severity=0.2,
    )

    assert resolved.contradiction_id == contradiction.contradiction_id
    assert resolved.claim_a_id == "claim-a"
    assert resolved.claim_b_id == "claim-b"
    assert resolved.status == "resolved"
    assert resolved.resolved_at is not None
    assert resolved.metadata["resolution_evidence_ids"] == ["m1", "m2"]
    assert len(engine.all()) == 2
    assert engine.latest() == [resolved]


def test_unresolved_contradiction_remains_open_in_latest(tmp_path):
    engine = ContradictionEngine(tmp_path / "contradictions.jsonl")
    contradiction = ContradictionRecord(
        contradiction_id="c1",
        created_at="2026-06-30T00:00:00+00:00",
        claim_a_id="claim-a",
        claim_b_id="claim-b",
        reason="claims conflict",
        severity=0.7,
    )

    engine.add_all([contradiction])

    assert engine.latest() == [contradiction]
    assert engine.latest()[0].status == "open"
