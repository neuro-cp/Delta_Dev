from integration.translation.text_to_signal_adapter import TextToSignalAdapter


def test_text_to_signal_adapter_is_deterministic():
    adapter = TextToSignalAdapter()

    payload = {
        "semantic_tokens": ["alpha"],
        "quantitative_fields": {"risk": 0.2},
        "role": "strategic_defense_advisor",
        "mode": "active",
        "confidence": 0.8,
    }

    signal_a = adapter.translate(payload)
    signal_b = adapter.translate(payload)

    assert signal_a == signal_b


def test_text_to_signal_adapter_validates_role():
    adapter = TextToSignalAdapter()

    bad_payload = {
        "semantic_tokens": ["alpha"],
        "quantitative_fields": {},
        "role": "invalid_role",
        "mode": "active",
    }

    try:
        adapter.translate(bad_payload)
        assert False
    except ValueError:
        assert True