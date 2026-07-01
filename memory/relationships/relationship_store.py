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
            weight=max(0.0, min(1.0, float(confidence))),
            reinforcement_count=1,
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

    def latest(self) -> List[RelationshipRecord]:
        records_by_id: dict[str, RelationshipRecord] = {}
        for record in self.all():
            records_by_id[record.relationship_id] = record
        return list(records_by_id.values())

    def for_memory(self, memory_id: str) -> List[RelationshipRecord]:
        return [
            record
            for record in self.latest()
            if record.source_id == memory_id or record.target_id == memory_id
        ]

    def find_equivalent(
        self,
        *,
        source_id: str,
        target_id: str,
        relationship_type: str,
    ) -> RelationshipRecord | None:
        for record in self.latest():
            if (
                record.source_id == str(source_id)
                and record.target_id == str(target_id)
                and record.relationship_type == str(relationship_type)
            ):
                return record
        return None

    def strengthen(
        self,
        relationship: RelationshipRecord,
        *,
        evidence: str,
        amount: float = 0.05,
        metadata: dict | None = None,
    ) -> RelationshipRecord:
        revised = RelationshipRecord(
            relationship_id=relationship.relationship_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_id=relationship.source_id,
            target_id=relationship.target_id,
            relationship_type=relationship.relationship_type,
            confidence=round(
                max(0.0, min(1.0, float(relationship.confidence) + float(amount))),
                4,
            ),
            weight=round(
                max(0.0, min(1.0, float(relationship.weight) + float(amount))),
                4,
            ),
            reinforcement_count=int(relationship.reinforcement_count) + 1,
            evidence=str(evidence),
            metadata={
                **relationship.metadata,
                **dict(metadata or {}),
                "previous_weight": relationship.weight,
                "strengthening_method": "append_only_weight_revision_v1",
            },
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(revised), sort_keys=True) + "\n")
        return revised
