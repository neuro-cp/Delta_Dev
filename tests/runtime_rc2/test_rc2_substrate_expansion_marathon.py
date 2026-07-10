from __future__ import annotations

from orchestration.runtime import rc2_substrate_expansion_marathon as expansion


def test_curriculum_generation_produces_high_quality_concepts():
    curriculum = expansion.build_curriculum_map(target_concepts=12)
    concepts = expansion._generate_concepts(curriculum, 12)

    assert len(concepts) == 12
    assert all(concept["canonical"] is False for concept in concepts)
    assert all(concept["approval_status"] == "approved_noncanonical" for concept in concepts)
    assert all(concept["training_performed"] is False for concept in concepts)
    assert all(concept["provider_calls_performed"] is False for concept in concepts)
    assert all(expansion.concept_quality_score(concept)[0] for concept in concepts)


def test_quality_gate_rejects_generic_concept():
    concept = {
        "concept_name": "What",
        "short_definition": "A reusable concept.",
        "propositions": ["weak"],
        "examples": [],
        "misconceptions": [],
        "related_concepts": ["meaning", "question"],
        "approval_status": "approved_noncanonical",
        "canonical": False,
    }

    ok, reasons, score = expansion.concept_quality_score(concept)

    assert ok is False
    assert score < 0.80
    assert "weak_name" in reasons
    assert "weak_definition" in reasons


def test_edge_quality_rejects_weak_or_self_links():
    edge = {
        "edge_id": "edge-1",
        "source_concept_id": "same",
        "target_concept_id": "same",
        "relation_type": "related_to",
        "confidence": 0.4,
        "supporting_propositions": [],
        "rollback_handle": "",
        "canonical": False,
        "approval_status": "approved_noncanonical",
    }

    ok, reasons = expansion.edge_quality_check(edge)

    assert ok is False
    assert "self_link" in reasons
    assert "weak_related_to" in reasons
    assert "low_confidence" in reasons


def test_generated_edges_are_typed_noncanonical_and_rollback_safe():
    curriculum = expansion.build_curriculum_map(target_concepts=20)
    concepts = expansion._generate_concepts(curriculum, 20)
    edges = expansion._generate_edges(concepts, max_target_edges=20)

    assert edges
    assert all(edge["relation_type"] != "related_to" for edge in edges)
    assert all(edge["canonical"] is False for edge in edges)
    assert all(edge["approval_status"] == "approved_noncanonical" for edge in edges)
    assert all(edge["rollback_handle"] for edge in edges)
    assert all(expansion.edge_quality_check(edge)[0] for edge in edges)
