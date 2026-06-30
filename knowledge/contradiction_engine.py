from __future__ import annotations

import re
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import List

from knowledge.contradiction_record import ContradictionRecord
from knowledge.semantic_record import SemanticKnowledgeRecord


class ContradictionEngine:
    """
    Detect and persist contradictions without deleting either claim.
    """

    NEGATORS = {"not", "never", "no", "cannot", "can't", "doesnt", "doesn't"}

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def detect_for(
        self,
        *,
        candidate: SemanticKnowledgeRecord,
        existing: List[SemanticKnowledgeRecord],
    ) -> List[ContradictionRecord]:
        records: List[ContradictionRecord] = []
        candidate_tokens = self._tokens(candidate.definition)
        candidate_negated = bool(candidate_tokens & self.NEGATORS)

        for record in existing:
            if record.concept_id == candidate.concept_id:
                continue
            tokens = self._tokens(record.definition)
            if not tokens:
                continue

            shared = len((candidate_tokens - self.NEGATORS) & (tokens - self.NEGATORS))
            if shared < 3:
                continue

            record_negated = bool(tokens & self.NEGATORS)
            if candidate_negated == record_negated:
                continue

            records.append(
                ContradictionRecord(
                    contradiction_id=str(uuid.uuid4()),
                    created_at=datetime.now(timezone.utc).isoformat(),
                    claim_a_id=record.concept_id,
                    claim_b_id=candidate.concept_id,
                    reason="Shared claim tokens with opposing negation.",
                    severity=0.5,
                    metadata={"shared_token_count": shared},
                )
            )

        return records

    def add_all(self, records: List[ContradictionRecord]) -> List[ContradictionRecord]:
        if not records:
            return []

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return records

    def all(self) -> List[ContradictionRecord]:
        if not self.path.exists():
            return []

        records: List[ContradictionRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(ContradictionRecord(**json.loads(line)))
        return records

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_']+", str(text).lower()))
