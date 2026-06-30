from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from learning.region.learning_record import (
    ConfidenceUpdate,
    LearningRecord,
    SemanticCandidate,
)


class LearningStore:
    """
    Append-only store for explicit learning records.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def add(self, record: LearningRecord) -> LearningRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def all(self) -> List[LearningRecord]:
        if not self.path.exists():
            return []

        records: List[LearningRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                records.append(
                    LearningRecord(
                        learning_id=payload["learning_id"],
                        created_at=payload["created_at"],
                        cycle_id=payload["cycle_id"],
                        semantic_candidates=[
                            SemanticCandidate(**item)
                            for item in payload.get("semantic_candidates", [])
                        ],
                        confidence_updates=[
                            ConfidenceUpdate(**item)
                            for item in payload.get("confidence_updates", [])
                        ],
                        questions=list(payload.get("questions", [])),
                        goal_candidates=list(payload.get("goal_candidates", [])),
                        consolidation_candidates=list(
                            payload.get("consolidation_candidates", [])
                        ),
                        metadata=dict(payload.get("metadata", {})),
                    )
                )
        return records
