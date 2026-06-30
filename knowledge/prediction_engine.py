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

        expectation = f"If this concept is relevant again, expect: {record.definition}"
        if self.find_equivalent(expectation) is not None:
            return None

        return PredictionRecord(
            prediction_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            source_concept_id=record.concept_id,
            expectation=expectation,
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

    def latest(self) -> List[PredictionRecord]:
        records_by_id: dict[str, PredictionRecord] = {}
        for record in self.all():
            records_by_id[record.prediction_id] = record
        return list(records_by_id.values())

    def find_equivalent(self, expectation: str) -> PredictionRecord | None:
        normalized = self._normalize(expectation)
        for record in self.latest():
            if self._normalize(record.expectation) == normalized:
                return record
        return None

    def validate_against_observations(self, observations: list) -> List[PredictionRecord]:
        validated: List[PredictionRecord] = []
        observation_records = [
            item
            for item in observations
            if getattr(item, "kind", "") in {"observation", "bootstrap_observation"}
        ]
        if not observation_records:
            return []

        for prediction in self.latest():
            if prediction.status != "open":
                continue
            prediction_tokens = self._tokens(prediction.expectation)
            support_ids = []
            for observation in observation_records:
                overlap = prediction_tokens & self._tokens(getattr(observation, "text", ""))
                if len(overlap) >= 3:
                    support_ids.append(observation.memory_id)
            if not support_ids:
                continue
            revised = PredictionRecord(
                prediction_id=prediction.prediction_id,
                created_at=datetime.now(timezone.utc).isoformat(),
                source_concept_id=prediction.source_concept_id,
                expectation=prediction.expectation,
                confidence=min(1.0, prediction.confidence + 0.05),
                status="supported",
                supporting_observations=list(
                    dict.fromkeys(prediction.supporting_observations + support_ids)
                ),
                failing_observations=list(prediction.failing_observations),
                metadata={**prediction.metadata, "validation": "token_overlap"},
            )
            validated.append(revised)
        self.add_all(validated)
        return validated

    @staticmethod
    def _tokens(text: str) -> set[str]:
        import re

        return set(re.findall(r"[a-z0-9_]+", str(text).lower()))

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(sorted(PredictionEngine._tokens(text)))
