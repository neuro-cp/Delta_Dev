from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InferenceRequest:
    prompt: str
    task_type: str = "open_ended"
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CanonicalInferenceResult:
    provider: str
    model_id: str
    answer: str
    raw_output: str
    confidence: float
    latency_seconds: float
    prompt_tokens: int
    response_tokens: int
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_ai_output_payload(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "raw_model_output": self.raw_output,
            "confidence": self.confidence,
            "canonical_inference": {
                "provider": self.provider,
                "model_id": self.model_id,
                "latency_seconds": self.latency_seconds,
                "prompt_tokens": self.prompt_tokens,
                "response_tokens": self.response_tokens,
                "evidence": list(self.evidence),
                "metadata": dict(self.metadata),
            },
        }
