from orchestration.input.inquiry_adapter import InquiryAdapter


def test_inquiry_adapter_from_text():
    packet = InquiryAdapter().adapt("Calculate 2 + 2")

    assert packet.raw_text == "Calculate 2 + 2"
    assert "calculate" in packet.semantic_tokens
    assert packet.quantitative_fields["n0"] == 2.0
    assert packet.quantitative_fields["n1"] == 2.0
