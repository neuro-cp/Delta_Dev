from dataclasses import dataclass

from orchestration.input.semantic_interpreter import SemanticInterpreter
from orchestration.schemas.inquiry_packet import InquiryPacket


@dataclass(frozen=True)
class DummyBundle:
    payload: dict
    confidence_band: float


class DummyModel:
    def produce_output(self, payload):
        return DummyBundle(payload={"raw_model_output": "ok"}, confidence_band=0.75)


def test_semantic_interpreter_adds_metadata():
    inquiry = InquiryPacket(inquiry_id="i1", raw_text="Compare Mars and Venus")
    enriched = SemanticInterpreter(model=DummyModel()).interpret(inquiry)

    assert "compare" in enriched.semantic_tokens
    assert enriched.metadata["entities"] == ["Compare", "Mars", "Venus"]
    assert enriched.metadata["model_advisory"]["raw_model_output"] == "ok"
    assert enriched.confidence == 0.75
