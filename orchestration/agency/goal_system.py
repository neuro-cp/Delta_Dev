from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List


@dataclass(frozen=True)
class GoalRecord:
    goal_id: str
    created_at: str
    updated_at: str
    description: str
    origin: str
    priority: float
    urgency: float
    progress: float = 0.0
    status: str = "active"
    dependencies: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    expected_value: float = 0.5
    estimated_effort: float = 0.5
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def action_pressure(self) -> float:
        remaining = 1.0 - max(0.0, min(1.0, self.progress))
        score = (
            self.priority * 0.3
            + self.urgency * 0.2
            + self.expected_value * 0.2
            + self.confidence * 0.1
            + remaining * 0.15
            - self.estimated_effort * 0.05
        )
        return round(max(0.0, min(1.0, score)), 4)


class GoalStore:
    """
    Append-only goal store.

    Newer records supersede older records by goal_id. Historical goal evolution
    remains inspectable.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def create(
        self,
        *,
        description: str,
        origin: str = "operator",
        priority: float = 0.5,
        urgency: float = 0.5,
        dependencies: Iterable[str] = (),
        supporting_evidence: Iterable[str] = (),
        contradicting_evidence: Iterable[str] = (),
        expected_value: float = 0.5,
        estimated_effort: float = 0.5,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> GoalRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = GoalRecord(
            goal_id=str(uuid.uuid4()),
            created_at=now,
            updated_at=now,
            description=str(description).strip(),
            origin=str(origin),
            priority=self._bounded(priority),
            urgency=self._bounded(urgency),
            dependencies=[str(item) for item in dependencies],
            supporting_evidence=[str(item) for item in supporting_evidence],
            contradicting_evidence=[str(item) for item in contradicting_evidence],
            expected_value=self._bounded(expected_value),
            estimated_effort=self._bounded(estimated_effort),
            confidence=self._bounded(confidence),
            metadata=dict(metadata or {}),
        )
        if not record.description:
            raise ValueError("goal description cannot be empty")
        return self.add(record)

    def add(self, record: GoalRecord) -> GoalRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def all(self) -> List[GoalRecord]:
        if not self.path.exists():
            return []
        records: List[GoalRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(GoalRecord(**json.loads(line)))
        return records

    def latest(self) -> List[GoalRecord]:
        records_by_id: dict[str, GoalRecord] = {}
        for record in self.all():
            records_by_id[record.goal_id] = record
        return list(records_by_id.values())

    def active(self) -> List[GoalRecord]:
        return [
            record
            for record in self.latest()
            if record.status == "active" and record.progress < 1.0
        ]

    @staticmethod
    def _bounded(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
