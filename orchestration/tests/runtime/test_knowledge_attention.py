from __future__ import annotations

from orchestration.runtime import ActivatedKnowledgeItem, KnowledgeActivation, KnowledgeAttentionFilter


def _item(concept_id: str, concept: str, definition: str, relevance: float = 0.1):
    return ActivatedKnowledgeItem(
        concept_id=concept_id,
        concept=concept,
        definition=definition,
        score=0.4,
        confidence=0.8,
        recommendation="Validated",
        promotion_score=0.58,
        source_store="test",
        metadata={"relevance": relevance, "projected_centrality": 0.2, "evidence_support": 1.0},
    )


def test_attention_filters_peripheral_activation_before_working_memory():
    activation = KnowledgeActivation(
        query="What causes GPS drift in dense cities?",
        items=[
            _item(
                "gps-multipath",
                "GPS multipath interference",
                "Dense buildings can reflect GPS signals and shift location estimates.",
            ),
            _item(
                "snow-plow-positioning",
                "Snowstorm plow positioning",
                "Cities should pre-position plows before severe snowstorms.",
            ),
        ],
    )

    attention = KnowledgeAttentionFilter().filter(activation)
    classes = {decision.concept_id: decision.classification for decision in attention.decisions}

    assert classes["gps-multipath"] == "Core"
    assert classes["snow-plow-positioning"] == "Peripheral"
    context = attention.as_working_memory_context(cycle_id="attention-test")
    assert [item.key for item in context.items] == ["gps-multipath"]


def test_attention_keeps_supporting_neighbors_out_of_discarded_state():
    activation = KnowledgeActivation(
        query="How should a city prepare for a severe snowstorm?",
        items=[
            _item(
                "snow-plow-positioning",
                "Snowstorm plow positioning",
                "Cities should pre-position plows before severe snowstorms.",
            ),
            _item(
                "shelter-capacity",
                "Shelter capacity planning",
                "Severe storm planning should compare shelter capacity against expected displaced population.",
            ),
        ],
    )

    attention = KnowledgeAttentionFilter().filter(activation)
    selected = {item.concept_id for item in attention.selected_items}

    assert "snow-plow-positioning" in selected
    assert "shelter-capacity" in selected
