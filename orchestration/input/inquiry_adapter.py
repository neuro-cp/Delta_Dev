from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Optional

from orchestration.schemas.inquiry_packet import InquiryPacket


class InquiryAdapter:
    """
    Raw input -> InquiryPacket.

    Pure normalization only.
    """

    def adapt(
        self,
        raw_input: str | Dict[str, Any],
        *,
        role: Optional[str] = None,
        mode: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> InquiryPacket:
        if isinstance(raw_input, dict):
            raw_text = str(raw_input.get("question") or raw_input.get("raw_text") or "").strip()
            semantic_tokens = list(raw_input.get("semantic_tokens", []))
            quantitative_fields = dict(raw_input.get("quantitative_fields", {}))
            role = raw_input.get("role", role)
            mode = raw_input.get("mode", mode)
            confidence = raw_input.get("confidence", confidence)
            metadata = {
                k: v
                for k, v in raw_input.items()
                if k not in {"question", "raw_text", "semantic_tokens", "quantitative_fields", "role", "mode", "confidence"}
            }
        else:
            raw_text = str(raw_input).strip()
            semantic_tokens = self._tokenize(raw_text)
            quantitative_fields = self._extract_numbers(raw_text)
            metadata = {}

        inquiry_id = self._make_inquiry_id(raw_text)

        return InquiryPacket(
            inquiry_id=inquiry_id,
            raw_text=raw_text,
            semantic_tokens=semantic_tokens,
            quantitative_fields=quantitative_fields,
            role=role,
            mode=mode,
            confidence=confidence,
            metadata=metadata,
        )

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9_]+", text.lower())

    @staticmethod
    def _extract_numbers(text: str) -> Dict[str, float]:
        values: Dict[str, float] = {}
        for idx, match in enumerate(re.findall(r"-?\d+(?:\.\d+)?", text)):
            values[f"n{idx}"] = float(match)
        return values

    @staticmethod
    def _make_inquiry_id(text: str) -> str:
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        return f"inquiry:{digest}"
