from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import List

from knowledge.contradiction_engine import ContradictionEngine
from knowledge.prediction_engine import PredictionEngine
from knowledge.semantic_record import SemanticKnowledgeRecord
from knowledge.semantic_store import SemanticKnowledgeStore
from learning.region import LearningRecord


class SemanticConsolidationEngine:
    """
    Promote selected learning candidates into semantic knowledge.

    Consolidation is explicit and non-destructive. Experience and learning
    records remain intact.
    """

    def __init__(
        self,
        *,
        semantic_store: SemanticKnowledgeStore,
        contradiction_engine: ContradictionEngine | None = None,
        prediction_engine: PredictionEngine | None = None,
    ) -> None:
        self._semantic_store = semantic_store
        self._contradiction_engine = contradiction_engine
        self._prediction_engine = prediction_engine

    def consolidate(
        self,
        learning_records: List[LearningRecord],
    ) -> dict:
        created: List[SemanticKnowledgeRecord] = []
        contradictions = []
        predictions = []

        existing = self._semantic_store.latest()

        for learning in learning_records:
            for candidate in learning.semantic_candidates:
                if hasattr(candidate, "text"):
                    text = candidate.text
                    evidence_ids = list(candidate.evidence_memory_ids)
                    confidence = float(candidate.confidence)
                    rationale = candidate.rationale
                else:
                    text = str(candidate.get("text", ""))
                    evidence_ids = list(candidate.get("evidence_memory_ids", []))
                    confidence = float(candidate.get("confidence", 0.0))
                    rationale = str(candidate.get("rationale", ""))

                if not text.strip():
                    continue

                equivalent = self._semantic_store.find_equivalent(text)
                if equivalent is not None:
                    continue

                related = self._semantic_store.find_related(text, threshold=0.65)
                now = datetime.now(timezone.utc).isoformat()
                record = SemanticKnowledgeRecord(
                    concept_id=str(uuid.uuid4()),
                    created_at=now,
                    updated_at=now,
                    concept=self._concept_name(text),
                    definition=text.strip(),
                    confidence=max(0.0, min(1.0, confidence)),
                    supporting_evidence=evidence_ids,
                    contradicting_evidence=[],
                    relationship_ids=[],
                    creation_source=f"learning:{learning.learning_id}",
                    last_validation=None,
                    revision_history=[item.concept_id for item in related],
                    metadata={
                        "cycle_id": learning.cycle_id,
                        "rationale": rationale,
                    },
                )

                self._semantic_store.add(record)
                created.append(record)

                if self._contradiction_engine is not None:
                    found = self._contradiction_engine.detect_for(
                        candidate=record,
                        existing=existing + created,
                    )
                    self._contradiction_engine.add_all(found)
                    contradictions.extend(found)

                if self._prediction_engine is not None:
                    prediction = self._prediction_engine.generate_for(record)
                    if prediction is not None:
                        self._prediction_engine.add_all([prediction])
                        predictions.append(prediction)

        return {
            "created": created,
            "contradictions": contradictions,
            "predictions": predictions,
        }

    @staticmethod
    def _concept_name(text: str) -> str:
        words = re.findall(r"[A-Za-z0-9_]+", text)
        return " ".join(words[:8]) if words else "unnamed concept"
