from __future__ import annotations

from orchestration.schemas.inquiry_packet import InquiryPacket
from orchestration.schemas.task_graph import TaskType


class TaskTypingEngine:
    """
    Deterministic task classifier.
    """

    def classify(self, inquiry: InquiryPacket) -> TaskType:
        text = inquiry.raw_text.lower()

        if any(op in text for op in ["+", "-", "*", "/", "calculate", "solve", "what is", "sum of"]) and inquiry.quantitative_fields:
            return TaskType.MATH

        if "compare" in text or ("difference" in text and "between" in text):
            return TaskType.COMPARISON

        if any(term in text for term in ["find", "lookup", "who is", "what is", "where is"]) and not inquiry.quantitative_fields:
            return TaskType.LOOKUP

        if any(term in text for term in ["diagnose", "why is", "failure", "problem", "issue", "cause"]):
            return TaskType.DIAGNOSTIC

        if any(term in text for term in ["plan", "steps", "roadmap", "strategy"]):
            return TaskType.PLANNING

        if len(text.split()) < 4:
            return TaskType.AMBIGUOUS

        return TaskType.OPEN_ENDED
