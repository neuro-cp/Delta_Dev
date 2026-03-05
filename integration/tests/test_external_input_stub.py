from integration.ai_surface.external_input_stub import ExternalInputStub


def test_external_input_stub_is_deterministic():
    stub = ExternalInputStub()

    payload = {
        "semantic_tokens": ["alpha"],
        "quantitative_fields": {"risk": 0.2},
    }

    bundle_a = stub.produce_output(payload)
    bundle_b = stub.produce_output(payload)

    assert bundle_a == bundle_b