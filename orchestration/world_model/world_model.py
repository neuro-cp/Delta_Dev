from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from orchestration.experience import GeneratedExperience


@dataclass(frozen=True)
class WorldModelObject:
    object_id: str
    label: str
    object_type: str
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorldModelEvent:
    event_id: str
    description: str
    event_type: str
    occurred_at: str | None = None
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorldModelRelation:
    relation_id: str
    source_id: str
    target_id: str
    relation_type: str
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


class WorldModelBuilder:
    """
    Build first-pass world-model records from governed experiences.
    """

    def build_from_experiences(
        self,
        experiences: Iterable[GeneratedExperience],
    ) -> dict[str, list[WorldModelObject] | list[WorldModelEvent] | list[WorldModelRelation]]:
        objects: list[WorldModelObject] = []
        events: list[WorldModelEvent] = []
        relations: list[WorldModelRelation] = []
        object_by_label: dict[str, WorldModelObject] = {}

        for experience in experiences:
            if experience.governance_status not in {"accepted", "supported", "validated"}:
                continue
            evidence_id = experience.experience_id
            labels = self._object_labels(experience.content)
            for label in labels:
                object_by_label.setdefault(
                    label,
                    WorldModelObject(
                        object_id=str(uuid.uuid4()),
                        label=label,
                        object_type=self._object_type(label),
                        evidence_ids=(evidence_id,),
                        metadata={"source_experience_type": experience.experience_type},
                    ),
                )

            event = WorldModelEvent(
                event_id=str(uuid.uuid4()),
                description=experience.content,
                event_type=experience.experience_type,
                occurred_at=experience.created_at,
                evidence_ids=(evidence_id,),
                metadata={"source": experience.source},
            )
            events.append(event)
            for item in object_by_label.values():
                if item.label in labels:
                    relations.append(
                        WorldModelRelation(
                            relation_id=str(uuid.uuid4()),
                            source_id=event.event_id,
                            target_id=item.object_id,
                            relation_type="mentions",
                            evidence_ids=(evidence_id,),
                        )
                    )

        objects = sorted(object_by_label.values(), key=lambda item: item.label)
        return {"objects": objects, "events": events, "relations": relations}

    def _object_labels(self, text: str) -> tuple[str, ...]:
        labels = []
        for match in re.findall(r"\b[A-Z][A-Za-z0-9_#-]*(?:\s+#?\d+)?", str(text)):
            label = " ".join(match.split())
            if len(label) > 1 and label not in labels:
                labels.append(label)
        return tuple(labels[:8])

    def _object_type(self, label: str) -> str:
        lower = label.lower()
        if "job" in lower:
            return "work_item"
        if "agent" in lower or "user" in lower or "contractor" in lower:
            return "agent"
        return "object"


class WorldModelStore:
    """
    Append-only world-model store.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def add_snapshot(
        self,
        *,
        objects: Iterable[WorldModelObject],
        events: Iterable[WorldModelEvent],
        relations: Iterable[WorldModelRelation],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        snapshot = {
            "snapshot_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "objects": self._jsonable(list(objects)),
            "events": self._jsonable(list(events)),
            "relations": self._jsonable(list(relations)),
            "metadata": dict(metadata or {}),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot, sort_keys=True) + "\n")
        return snapshot

    def all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _jsonable(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._jsonable(asdict(value))
        if isinstance(value, dict):
            return {str(key): self._jsonable(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return [self._jsonable(item) for item in value]
        if isinstance(value, list):
            return [self._jsonable(item) for item in value]
        return value
