from integration.transformation.structured_signal import StructuredCognitiveSignal

def test_structured_signal_instantiates():
    signal = StructuredCognitiveSignal(
        semantic_tokens=["alpha"],
        quantitative_fields={"prob": 0.5},
        role="strategic_defense_advisor",
        mode="active",
        confidence=0.8,
    )

    assert signal.semantic_tokens == ["alpha"]
