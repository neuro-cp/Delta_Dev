from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class InquiryPacket:
    """
    Canonical normalized inquiry object.

    This is the first stable boundary for the orchestration layer.
    It is descriptive only and carries no execution authority.
    """

    inquiry_id: str
    raw_text: str

    semantic_tokens: List[str] = field(default_factory=list)
    quantitative_fields: Dict[str, float] = field(default_factory=dict)

    role: Optional[str] = None
    mode: Optional[str] = None
    confidence: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)
