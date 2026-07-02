from __future__ import annotations

from datetime import datetime, timezone

from knowledge import SemanticKnowledgeRecord, SemanticKnowledgeStore
from memory.persistent import MemoryStore
from memory.relationships import RelationshipStore
from tools.phase21_relationship_centrality_audit import audit_relationship_centrality


def test_relationship_audit_detects_memory_projection_gap(tmp_path):
    store_root = tmp_path / "store"
    reports_dir = tmp_path / "reports"
    memory = MemoryStore(store_root / "memory.jsonl")
    relationships = RelationshipStore(store_root / "relationships.jsonl")
    knowledge = SemanticKnowledgeStore(store_root / "knowledge.jsonl")
    first = memory.add(kind="observation", text="first", source="test")
    second = memory.add(kind="observation", text="second", source="test")
    relationships.add(
        source_id=first.memory_id,
        target_id=second.memory_id,
        relationship_type="temporal_sequence",
        confidence=0.8,
    )
    now = datetime.now(timezone.utc).isoformat()
    knowledge.add(
        SemanticKnowledgeRecord(
            concept_id="concept-a",
            created_at=now,
            updated_at=now,
            concept="Memory relationship projection",
            definition="Semantic concepts may inherit evidence memory relationships.",
            confidence=0.8,
            supporting_evidence=[first.memory_id],
            creation_source="test",
        )
    )

    summary = audit_relationship_centrality(
        store_root=store_root,
        reports_dir=reports_dir,
        sample_size=1,
    )

    assert summary["relationship_endpoint_counts"]["memory_to_memory"] == 1
    assert summary["concepts_with_direct_semantic_edges"] == 0
    assert summary["concepts_with_projected_memory_edges"] == 1
    assert summary["diagnosis_counts"]["memory_graph_not_projected"] == 1
    assert (reports_dir / "phase21_relationship_centrality_audit.md").exists()
