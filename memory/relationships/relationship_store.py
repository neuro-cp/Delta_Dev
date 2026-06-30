from __future__ import annotations

import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from memory.relationships.relationship_record import RelationshipRecord


class RelationshipStore:
    """
    Append-only relationship store.

    Relationships link memories without rewriting them.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def add(
        self,
        *,
        source_id: str,
        target_id: str,
        relationship_type: str,
        confidence: float = 1.0,
        evidence: str = "",
        metadata: dict | None = None,
    ) -> RelationshipRecord:
        record = RelationshipRecord(
            relationship_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            source_id=str(source_id),
            target_id=str(target_id),
            relationship_type=str(relationship_type),
            confidence=max(0.0, min(1.0, float(confidence))),
            evidence=str(evidence),
            metadata=dict(metadata or {}),
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

        return record

    def all(self) -> List[RelationshipRecord]:
        if not self.path.exists():
            return []

        records: List[RelationshipRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(RelationshipRecord(**json.loads(line)))
        return records

    def for_memory(self, memory_id: str) -> List[RelationshipRecord]:
        return [
            record
            for record in self.all()
            if record.source_id == memory_id or record.target_id == memory_id
        ]
