from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from integration.model_runtime.inference_types import CanonicalInferenceResult


@dataclass(frozen=True)
class ModelInferenceRecord:
    inference_id: str
    created_at: str
    provider: str
    model_id: str
    route: str
    task_type: str
    prompt_tokens: int
    response_tokens: int
    latency_seconds: float
    confidence: float
    evidence_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelObservatory:
    """
    Append-only observability store for model inference behavior.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(
        self,
        *,
        result: CanonicalInferenceResult,
        route: str,
        task_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> ModelInferenceRecord:
        record = ModelInferenceRecord(
            inference_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            provider=result.provider,
            model_id=result.model_id,
            route=str(route),
            task_type=str(task_type),
            prompt_tokens=int(result.prompt_tokens),
            response_tokens=int(result.response_tokens),
            latency_seconds=float(result.latency_seconds),
            confidence=float(result.confidence),
            evidence_count=len(result.evidence),
            metadata={**result.metadata, **dict(metadata or {})},
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def all(self) -> list[ModelInferenceRecord]:
        if not self.path.exists():
            return []
        records: list[ModelInferenceRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(ModelInferenceRecord(**json.loads(line)))
        return records

    def metrics(self) -> dict[str, Any]:
        records = self.all()
        if not records:
            return {
                "total": 0,
                "by_model": {},
                "average_latency_seconds": None,
                "average_confidence": None,
            }
        by_model: dict[str, int] = {}
        for record in records:
            by_model[record.model_id] = by_model.get(record.model_id, 0) + 1
        return {
            "total": len(records),
            "by_model": dict(sorted(by_model.items())),
            "average_latency_seconds": round(
                sum(record.latency_seconds for record in records) / len(records),
                4,
            ),
            "average_confidence": round(
                sum(record.confidence for record in records) / len(records),
                4,
            ),
        }
