from orchestration.input.inquiry_adapter import InquiryAdapter


def test_inquiry_adapter_from_text():
    packet = InquiryAdapter().adapt("Calculate 2 + 2")

    assert packet.raw_text == "Calculate 2 + 2"
    assert "calculate" in packet.semantic_tokens
    assert packet.quantitative_fields["n0"] == 2.0
    assert packet.quantitative_fields["n1"] == 2.0


def test_dict_input_derives_tokens_and_numbers_from_question():
    inquiry = InquiryAdapter().adapt(
        {
            "question": "What is 4 + 6?",
            "attended_context": [],
        }
    )

    assert inquiry.raw_text == "What is 4 + 6?"
    assert inquiry.semantic_tokens == ["what", "is", "4", "6"]
    assert inquiry.quantitative_fields == {"n0": 4.0, "n1": 6.0}
    assert inquiry.metadata == {"attended_context": []}


def test_dict_input_preserves_explicit_tokens_and_numbers():
    inquiry = InquiryAdapter().adapt(
        {
            "question": "What is 4 + 6?",
            "semantic_tokens": ["custom"],
            "quantitative_fields": {"answer": 10.0},
        }
    )

    assert inquiry.semantic_tokens == ["custom"]
    assert inquiry.quantitative_fields == {"answer": 10.0}
