from __future__ import annotations

import re
from typing import Any, Dict, Optional

from orchestration.schemas.inquiry_packet import InquiryPacket


class SemanticInterpreter:
    """
    Thin semantic enrichment layer.

    Behavior:
    - rule-based extraction always available
    - optional advisory call into an external model surface
    - no hard dependency on specific runtime classes
    """

    def __init__(self, model: Optional[Any] = None) -> None:
        self._model = model

    def interpret(self, inquiry: InquiryPacket) -> InquiryPacket:
        tokens = list(inquiry.semantic_tokens)
        metadata = dict(inquiry.metadata)

        extracted = self._extract_semantics(inquiry.raw_text)
        for token in extracted["semantic_tokens"]:
            if token not in tokens:
                tokens.append(token)

        metadata["entities"] = extracted["entities"]
        metadata["constraint_phrases"] = extracted["constraint_phrases"]
        metadata["question_mark"] = inquiry.raw_text.endswith("?")

        advisory_confidence = inquiry.confidence

        if self._model is not None:
            payload = {"question": inquiry.raw_text}
            result = self._model.produce_output(payload)
            raw_payload = getattr(result, "payload", {}) if result is not None else {}
            advisory_confidence = getattr(result, "confidence_band", advisory_confidence)
            metadata["model_advisory"] = dict(raw_payload)

        return InquiryPacket(
            inquiry_id=inquiry.inquiry_id,
            raw_text=inquiry.raw_text,
            semantic_tokens=tokens,
            quantitative_fields=dict(inquiry.quantitative_fields),
            role=inquiry.role,
            mode=inquiry.mode,
            confidence=advisory_confidence,
            metadata=metadata,
        )

    @staticmethod
    def _extract_semantics(text: str) -> Dict[str, object]:
        lower = text.lower()

        entities = re.findall(r"\b[A-Z][A-Za-z0-9_-]+\b", text)
        constraint_phrases = []

        markers = [
            "must",
            "should",
            "compare",
            "diagnose",
            "plan",
            "lookup",
            "find",
            "calculate",
            "explain",
        ]
        for marker in markers:
            if marker in lower:
                constraint_phrases.append(marker)

        semantic_tokens = list(dict.fromkeys(re.findall(r"[a-z0-9_]+", lower)))

        return {
            "entities": entities,
            "constraint_phrases": constraint_phrases,
            "semantic_tokens": semantic_tokens,
        }
