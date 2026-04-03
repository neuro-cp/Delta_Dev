from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskType
from orchestration.structuring.task_typing_engine import TaskTypingEngine


def test_task_typing_math():
    inquiry = InquiryPacket(
        inquiry_id="i1",
        raw_text="What is 2 + 2?",
        quantitative_fields={"n0": 2.0, "n1": 2.0},
    )
    assert TaskTypingEngine().classify(inquiry) == TaskType.MATH


def test_task_typing_comparison():
    inquiry = InquiryPacket(inquiry_id="i2", raw_text="Compare alpha and beta")
    assert TaskTypingEngine().classify(inquiry) == TaskType.COMPARISON
