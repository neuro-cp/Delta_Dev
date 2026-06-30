from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord


class PredictionEngine:
    """
    Generate open predictions from sufficiently confident knowledge.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def generate_for(
        self,
        record: SemanticKnowledgeRecord,
        *,
        threshold: float = 0.6,
    ) -> PredictionRecord | None:
        if record.confidence < threshold:
            return None

        return PredictionRecord(
            prediction_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            source_concept_id=record.concept_id,
            expectation=f"If this concept is relevant again, expect: {record.definition}",
            confidence=max(0.0, min(1.0, record.confidence * 0.8)),
            metadata={"concept": record.concept},
        )

    def add_all(self, records: List[PredictionRecord]) -> List[PredictionRecord]:
        if not records:
            return []

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return records

    def all(self) -> List[PredictionRecord]:
        if not self.path.exists():
            return []

        records: List[PredictionRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(PredictionRecord(**json.loads(line)))
        return records
