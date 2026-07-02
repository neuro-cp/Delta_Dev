from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest

from knowledge import ContradictionEngine, SemanticKnowledgeRecord, SemanticKnowledgeStore
from knowledge.contradiction_record import ContradictionRecord
from knowledge.prediction_engine import PredictionEngine
from knowledge.prediction_record import PredictionRecord
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from tools.continuous_learning_operator import run_continuous_learning
from tools.promotion_governance import run_promotion_governance


def _record(
    *,
    concept_id: str,
    concept: str,
    confidence: float = 0.82,
    cycle_id: str = "cycle-a",
) -> SemanticKnowledgeRecord:
    now = datetime.now(timezone.utc).isoformat()
    return SemanticKnowledgeRecord(
        concept_id=concept_id,
        created_at=now,
        updated_at=now,
        concept=concept,
        definition=f"{concept} is supported when validation evidence is present.",
        confidence=confidence,
        supporting_evidence=["evidence-a", "evidence-b"],
        creation_source="test",
        metadata={"cycle_id": cycle_id},
    )


def test_promotion_governance_scores_every_latest_concept(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    memory = MemoryStore(store_root / "memory.jsonl")
    good = knowledge.add(_record(concept_id="good", concept="Validated planning constraints"))
    weak = knowledge.add(_record(concept_id="weak", concept="The evidence that would change the answer is"))
    memory.add(
        kind="orchestration_output",
        text="planning output",
        source="delta:llm",
        tags=["cycle", "output", "planning", "qwen2-5-7b-instruct-q4-k-m"],
        metadata={"cycle_id": "cycle-a"},
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-good",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=good.concept_id,
                expectation="If relevant, expect planning constraints.",
                confidence=0.7,
                status="supported",
                supporting_observations=["obs"],
            ),
            PredictionRecord(
                prediction_id="p-weak",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=weak.concept_id,
                expectation="If relevant, expect prompt artifact.",
                confidence=0.4,
                status="failed",
                failing_observations=["obs"],
            ),
        ]
    )

    summary = run_promotion_governance(store_root=store_root, reports_dir=reports_dir)

    assert summary["concepts_evaluated"] == 2
    by_concept = {item["concept_id"]: item for item in summary["decisions"]}
    assert by_concept["good"]["recommendation"] in {"Candidate", "Validated", "Promotion Eligible"}
    assert by_concept["weak"]["recommendation"] == "Reject"
    assert by_concept["good"]["provenance"]["source_provider"] == "qwen"
    assert (reports_dir / "promotion_governance_report.md").exists()
    assert (reports_dir / "promotion_candidates.md").exists()
    assert (reports_dir / "promotion_rejections.md").exists()
    assert (reports_dir / "concept_lifecycle_report.md").exists()


def test_promotion_governance_blocks_open_contradictions(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    contradictions = ContradictionEngine(store_root / "contradictions.jsonl")
    record = knowledge.add(_record(concept_id="contradicted", concept="Contradicted claim"))
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-supported",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="If relevant, expect support.",
                confidence=0.7,
                status="supported",
            )
        ]
    )
    contradictions.add_all(
        [
            ContradictionRecord(
                contradiction_id="c1",
                created_at=datetime.now(timezone.utc).isoformat(),
                claim_a_id=record.concept_id,
                claim_b_id="other",
                reason="test",
                severity=0.5,
                status="open",
            )
        ]
    )

    summary = run_promotion_governance(store_root=store_root, reports_dir=reports_dir)

    assert summary["decisions"][0]["recommendation"] == "Reject"
    assert summary["decisions"][0]["evidence"]["open_contradictions"] == 1


def test_recovered_normalized_concept_is_not_hard_rejected_for_source_failure(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    record = knowledge.add(
        SemanticKnowledgeRecord(
            **{
                **_record(
                    concept_id="normalized",
                    concept="Risk assessment separates likelihood from impact",
                    confidence=0.86,
                ).__dict__,
                "metadata": {
                    "phase18_normalization": {
                        "original_concept": "Likelihood refers to the probability of a risk",
                        "method": "risk_likelihood_impact_template",
                        "source_provider": "qwen",
                        "source_profile": "risk_assessment",
                    }
                },
            }
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-old",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="pre-normalization failure",
                confidence=0.4,
                status="failed",
            ),
            PredictionRecord(
                prediction_id="p-new",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="post-normalization support",
                confidence=0.7,
                status="supported",
            ),
        ]
    )

    summary = run_promotion_governance(store_root=store_root, reports_dir=reports_dir)

    decision = summary["decisions"][0]
    assert decision["evidence"]["failed_predictions"] == 1
    assert decision["evidence"]["effective_failed_predictions"] == 0
    assert decision["recommendation"] != "Reject"


def test_clean_supported_central_concept_can_be_promotion_eligible(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    record = knowledge.add(
        _record(
            concept_id="eligible",
            concept="Validated constraints improve planning reliability",
            confidence=0.9,
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-eligible",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="If relevant, expect validated constraints to improve planning reliability.",
                confidence=0.75,
                status="supported",
            )
        ]
    )
    for index in range(8):
        relationships.add(
            source_id=record.concept_id,
            target_id=f"related-{index}",
            relationship_type="supports",
            confidence=0.9,
            evidence="test centrality",
        )

    summary = run_promotion_governance(store_root=store_root, reports_dir=reports_dir)

    assert summary["decisions"][0]["recommendation"] == "Promotion Eligible"


def test_incomplete_supported_concept_is_not_promotion_eligible(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    record = knowledge.add(
        _record(
            concept_id="fragment",
            concept="If the priority group changes it may require",
            confidence=0.9,
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-fragment",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="If relevant, expect priority group changes.",
                confidence=0.75,
                status="supported",
            )
        ]
    )
    for index in range(8):
        relationships.add(
            source_id=record.concept_id,
            target_id=f"related-{index}",
            relationship_type="supports",
            confidence=0.9,
            evidence="test centrality",
        )

    summary = run_promotion_governance(store_root=store_root, reports_dir=reports_dir)

    assert summary["decisions"][0]["evidence"]["incomplete_proposition"] is True
    assert summary["decisions"][0]["recommendation"] != "Promotion Eligible"

    projected = run_promotion_governance(
        store_root=store_root,
        reports_dir=tmp_path / "projected_fragment",
        use_projection=True,
    )
    assert projected["decisions"][0]["recommendation"] not in {
        "Validated",
        "Promotion Eligible",
    }


@pytest.mark.parametrize(
    "concept",
    [
        "The cycle can be completed by predicting that",
        "Evidence that would require reallocation includes a significant",
        "The next operational risk is that the forecasted",
        "Allocating resources for emergency shelters requires prioritizing based",
        "For instance if a previous handoff was delayed",
        "If the large tent is allocated to one",
        "When a permit assumption fails the emergency response",
        "To predict a handoff failure status updates should",
    ],
)
def test_audit_fragment_shapes_are_incomplete(tmp_path, concept):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    record = knowledge.add(
        _record(
            concept_id="fragment",
            concept=concept,
            confidence=0.9,
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-fragment",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="If relevant, expect the fragment to remain blocked.",
                confidence=0.75,
                status="supported",
            )
        ]
    )
    for index in range(8):
        relationships.add(
            source_id=record.concept_id,
            target_id=f"related-{index}",
            relationship_type="supports",
            confidence=0.9,
            evidence="test centrality",
        )

    summary = run_promotion_governance(
        store_root=store_root,
        reports_dir=reports_dir,
        use_projection=True,
    )

    assert summary["decisions"][0]["evidence"]["incomplete_proposition"] is True
    assert summary["decisions"][0]["recommendation"] not in {
        "Validated",
        "Promotion Eligible",
    }


def test_complete_conditional_can_remain_promotion_eligible(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    record = knowledge.add(
        _record(
            concept_id="conditional",
            concept="If validated constraints are unavailable, planning reliability decreases",
            confidence=0.9,
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-conditional",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="If relevant, expect missing constraints to reduce reliability.",
                confidence=0.75,
                status="supported",
            )
        ]
    )
    for index in range(8):
        relationships.add(
            source_id=record.concept_id,
            target_id=f"related-{index}",
            relationship_type="supports",
            confidence=0.9,
            evidence="test centrality",
        )

    summary = run_promotion_governance(store_root=store_root, reports_dir=reports_dir)

    assert summary["decisions"][0]["evidence"]["incomplete_proposition"] is False
    assert summary["decisions"][0]["recommendation"] == "Promotion Eligible"


def test_projection_disabled_matches_default_governance(tmp_path):
    store_root = tmp_path / "store"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    record = knowledge.add(_record(concept_id="stable", concept="Stable validated concept"))
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-stable",
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=record.concept_id,
                expectation="If relevant, expect support.",
                confidence=0.7,
                status="supported",
            )
        ]
    )

    default = run_promotion_governance(
        store_root=store_root,
        reports_dir=tmp_path / "default",
    )
    explicit = run_promotion_governance(
        store_root=store_root,
        reports_dir=tmp_path / "explicit",
        use_projection=False,
    )

    assert default["decisions"][0]["promotion_score"] == explicit["decisions"][0]["promotion_score"]
    assert default["decisions"][0]["recommendation"] == explicit["decisions"][0]["recommendation"]
    assert default["virtual_projection_enabled"] is False


def test_virtual_projection_uses_supporting_memory_relationships(tmp_path):
    store_root = tmp_path / "store"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    first = memory.add(kind="observation", text="first evidence", source="test")
    second = memory.add(kind="observation", text="second evidence", source="test")
    relationships.add(
        source_id=first.memory_id,
        target_id=second.memory_id,
        relationship_type="temporal_sequence",
        confidence=0.8,
    )
    now = datetime.now(timezone.utc).isoformat()
    record = knowledge.add(
        SemanticKnowledgeRecord(
            concept_id="projected",
            created_at=now,
            updated_at=now,
            concept="Evidence memory links support centrality",
            definition="Evidence memory links support centrality when projected.",
            confidence=0.86,
            supporting_evidence=[first.memory_id],
            creation_source="test",
        )
    )
    predictions.add_all(
        [
            PredictionRecord(
                prediction_id="p-projected",
                created_at=now,
                source_concept_id=record.concept_id,
                expectation="If relevant, expect projected centrality.",
                confidence=0.7,
                status="supported",
            )
        ]
    )

    raw = run_promotion_governance(
        store_root=store_root,
        reports_dir=tmp_path / "raw",
        use_projection=False,
    )
    projected = run_promotion_governance(
        store_root=store_root,
        reports_dir=tmp_path / "projected",
        use_projection=True,
    )

    assert raw["decisions"][0]["dimensions"]["relationship_centrality"] == 0.0
    assert projected["decisions"][0]["dimensions"]["relationship_centrality"] > 0.0
    assert (
        "supporting_evidence_memory_relationships"
        in projected["decisions"][0]["evidence"]["projection_sources"]
    )


def test_virtual_projection_uses_shared_supporting_evidence(tmp_path):
    store_root = tmp_path / "store"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    memory = MemoryStore(store_root / "memory.jsonl")
    predictions = PredictionEngine(store_root / "predictions.jsonl")
    evidence = memory.add(kind="observation", text="shared evidence", source="test")
    now = datetime.now(timezone.utc).isoformat()
    for concept_id, concept in (
        ("left", "Shared evidence left concept"),
        ("right", "Shared evidence right concept"),
    ):
        record = knowledge.add(
            SemanticKnowledgeRecord(
                concept_id=concept_id,
                created_at=now,
                updated_at=now,
                concept=concept,
                definition=f"{concept} is supported by shared evidence.",
                confidence=0.84,
                supporting_evidence=[evidence.memory_id],
                creation_source="test",
            )
        )
        predictions.add_all(
            [
                PredictionRecord(
                    prediction_id=f"p-{concept_id}",
                    created_at=now,
                    source_concept_id=record.concept_id,
                    expectation="If relevant, expect shared support.",
                    confidence=0.7,
                    status="supported",
                )
            ]
        )

    projected = run_promotion_governance(
        store_root=store_root,
        reports_dir=tmp_path / "projected",
        use_projection=True,
    )

    assert all(
        decision["evidence"]["shared_evidence_neighbor_concepts"] == 1
        for decision in projected["decisions"]
    )
    assert all(
        "shared_supporting_evidence" in decision["evidence"]["projection_sources"]
        for decision in projected["decisions"]
    )


def test_virtual_projection_does_not_mutate_store_files(tmp_path):
    store_root = tmp_path / "store"
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    evidence = memory.add(kind="observation", text="first evidence", source="test")
    other = memory.add(kind="observation", text="second evidence", source="test")
    relationships.add(
        source_id=evidence.memory_id,
        target_id=other.memory_id,
        relationship_type="temporal_sequence",
        confidence=0.8,
    )
    now = datetime.now(timezone.utc).isoformat()
    knowledge.add(
        SemanticKnowledgeRecord(
            concept_id="readonly",
            created_at=now,
            updated_at=now,
            concept="Read only projection",
            definition="Read only projection must not mutate stores.",
            confidence=0.8,
            supporting_evidence=[evidence.memory_id],
            creation_source="test",
        )
    )
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in store_root.glob("*.jsonl")
    }

    run_promotion_governance(
        store_root=store_root,
        reports_dir=tmp_path / "reports",
        use_projection=True,
    )

    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in store_root.glob("*.jsonl")
    }
    assert after == before


def test_continuous_operator_enforces_bounded_cycles(tmp_path):
    with pytest.raises(ValueError):
        run_continuous_learning(
            store_root=tmp_path / "store",
            reports_dir=tmp_path / "reports",
            cycles=201,
        )
