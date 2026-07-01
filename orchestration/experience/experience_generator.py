from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.model_runtime import CanonicalInferenceResult


EXPERIENCE_TYPES: tuple[str, ...] = (
    "observation",
    "hypothesis",
    "plan",
    "simulation",
    "prediction",
    "reflection",
)


@dataclass(frozen=True)
class ExperienceRequest:
    prompt: str
    required_experience_types: tuple[str, ...] = EXPERIENCE_TYPES
    source: str = "reasoning_provider"
    curriculum_case_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratedExperience:
    experience_id: str
    created_at: str
    experience_type: str
    content: str
    source: str
    governance_status: str = "pending"
    direct_knowledge_promotion: bool = False
    evidence_ids: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class ExperienceGenerator:
    """
    Convert provider output into governed experience candidates.

    Generated experiences are not knowledge. They require downstream evidence,
    validation, and governance before any semantic promotion.
    """

    def generate(
        self,
        *,
        request: ExperienceRequest,
        provider_output: CanonicalInferenceResult | AIOutputBundle | dict[str, Any] | str,
    ) -> list[GeneratedExperience]:
        payload = self._payload(provider_output)
        provider_text = self._text(payload)
        records: list[GeneratedExperience] = []
        for experience_type in request.required_experience_types:
            normalized_type = str(experience_type).strip().lower()
            if normalized_type not in EXPERIENCE_TYPES:
                continue
            content = self._content_for(
                experience_type=normalized_type,
                prompt=request.prompt,
                provider_text=provider_text,
                payload=payload,
            )
            records.append(
                GeneratedExperience(
                    experience_id=str(uuid.uuid4()),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    experience_type=normalized_type,
                    content=content,
                    source=request.source,
                    provenance=self._provenance(payload),
                    metadata={
                        **request.metadata,
                        "curriculum_case_id": request.curriculum_case_id,
                        "prompt": request.prompt,
                        "experience_generator": "v1",
                    },
                )
            )
        return records

    def _payload(
        self,
        provider_output: CanonicalInferenceResult | AIOutputBundle | dict[str, Any] | str,
    ) -> dict[str, Any]:
        if isinstance(provider_output, CanonicalInferenceResult):
            return {
                "provider": provider_output.provider,
                "model_id": provider_output.model_id,
                "answer": provider_output.answer,
                "raw_output": provider_output.raw_output,
                "confidence": provider_output.confidence,
                "evidence": list(provider_output.evidence),
                "metadata": dict(provider_output.metadata),
            }
        if isinstance(provider_output, AIOutputBundle):
            return {
                "provider": provider_output.mode,
                "model_id": provider_output.payload.get("model_id"),
                "answer": provider_output.payload.get("answer")
                or provider_output.payload.get("raw_model_output")
                or "",
                "raw_output": provider_output.payload.get("raw_model_output", ""),
                "confidence": provider_output.confidence_band,
                "evidence": provider_output.payload.get("evidence", []),
                "metadata": dict(provider_output.payload),
            }
        if isinstance(provider_output, dict):
            return dict(provider_output)
        return {"answer": str(provider_output), "raw_output": str(provider_output)}

    def _text(self, payload: dict[str, Any]) -> str:
        text = payload.get("answer") or payload.get("raw_output") or ""
        return str(text).strip()

    def _content_for(
        self,
        *,
        experience_type: str,
        prompt: str,
        provider_text: str,
        payload: dict[str, Any],
    ) -> str:
        structured = payload.get(experience_type)
        if structured:
            return str(structured).strip()
        if provider_text:
            return f"{experience_type}: {provider_text}"
        return f"{experience_type}: generated candidate experience for {prompt}"

    def _provenance(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": payload.get("provider"),
            "model_id": payload.get("model_id"),
            "confidence": payload.get("confidence"),
            "evidence": list(payload.get("evidence", []) or []),
        }


class ExperienceStore:
    """
    Append-only store for generated experiences awaiting governance.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def add_many(self, records: Iterable[GeneratedExperience]) -> list[GeneratedExperience]:
        items = list(records)
        if not items:
            return []
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for record in items:
                handle.write(json.dumps(self._jsonable(record), sort_keys=True) + "\n")
        return items

    def all(self) -> list[GeneratedExperience]:
        if not self.path.exists():
            return []
        records: list[GeneratedExperience] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                records.append(
                    GeneratedExperience(
                        experience_id=payload["experience_id"],
                        created_at=payload["created_at"],
                        experience_type=payload["experience_type"],
                        content=payload["content"],
                        source=payload["source"],
                        governance_status=payload.get("governance_status", "pending"),
                        direct_knowledge_promotion=bool(
                            payload.get("direct_knowledge_promotion", False)
                        ),
                        evidence_ids=tuple(payload.get("evidence_ids", [])),
                        provenance=dict(payload.get("provenance", {})),
                        metadata=dict(payload.get("metadata", {})),
                    )
                )
        return records

    def _jsonable(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._jsonable(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [self._jsonable(item) for item in value]
        if isinstance(value, list):
            return [self._jsonable(item) for item in value]
        return value
