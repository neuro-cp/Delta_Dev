from __future__ import annotations

import json
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from knowledge.prediction_record import PredictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord
from memory.persistent.memory_record import MemoryRecord


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
            metadata={"concept": record.concept,
                      "source_evidence_ids": list(record.supporting_evidence)},
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

    def validate_against_observations(self, observations: list[MemoryRecord]) -> List[PredictionRecord]:
        """Apply explicit external outcome assessments, never lexical similarity.

        The caller supplies persisted observations. An outcome needs a prediction
        ID, supported/failed verdict and validation_source in metadata. Assessments
        are attributed reports, not independent proof that the source is correct.
        """
        validated: List[PredictionRecord] = []
        outcomes_by_id: dict[str, list[tuple[MemoryRecord, datetime]]] = {}
        for observation in observations:
            metadata = observation.metadata
            prediction_id = metadata.get("prediction_id")
            allowed_source = observation.source == "operator" or observation.source.startswith(
                ("sensor:", "tool:", "test:")
            )
            if (
                observation.kind != "prediction_outcome" or not allowed_source
                or not isinstance(prediction_id, str)
                or metadata.get("outcome") not in {"supported", "failed"}
                or not isinstance(metadata.get("validation_source"), str)
                or not metadata["validation_source"].strip()
            ):
                continue
            observed = self._parse_time(observation.created_at)
            if observed is not None:
                outcomes_by_id.setdefault(prediction_id, []).append((observation, observed))
        if not outcomes_by_id:
            return []
        for prediction in self.latest():
            if prediction.status != "open":
                continue
            created = self._parse_time(prediction.created_at)
            if created is None:
                continue
            matches = {}
            source_ids = set(prediction.metadata.get("source_evidence_ids", []))
            for observation, observed in outcomes_by_id.get(prediction.prediction_id, []):
                if observed > created and observation.memory_id not in source_ids:
                    matches[observation.memory_id] = observation
            outcomes = {item.metadata["outcome"] for item in matches.values()}
            # Conflicting assessments require review; their input order is not evidence.
            if len(outcomes) != 1:
                continue
            outcome = outcomes.pop()
            evidence_ids = list(matches)
            revised = replace(
                prediction,
                status=outcome,
                supporting_observations=(evidence_ids if outcome == "supported" else []),
                failing_observations=(evidence_ids if outcome == "failed" else []),
                metadata={**prediction.metadata,
                          "validation": "explicit_outcome_v1",
                          "last_validated": datetime.now(timezone.utc).isoformat(),
                          "validation_sources": sorted({
                              item.metadata["validation_source"] for item in matches.values()
                          })},
            )
            validated.append(revised)
        self.add_all(validated)
        return validated

    @staticmethod
    def is_evaluated(record: PredictionRecord) -> bool:
        evidence = (record.supporting_observations if record.status == "supported"
                    else record.failing_observations if record.status == "failed" else [])
        return bool(evidence and record.metadata.get("validation") == "explicit_outcome_v1")

    @staticmethod
    def _parse_time(value: str) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(str(text).casefold().split())
