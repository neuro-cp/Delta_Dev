from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

from memory.persistent.memory_record import MemoryRecord


class MemoryStore:
    """
    Append-only JSONL store for durable Delta memories.

    This is intentionally simple. It establishes a stable persistence surface
    before adding indexing, consolidation, or relationship modeling.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def add(
        self,
        *,
        text: str,
        kind: str = "experience",
        source: str = "operator",
        layer: str = "experience",
        confidence: float = 1.0,
        tags: Iterable[str] = (),
        metadata: dict | None = None,
    ) -> MemoryRecord:
        normalized = str(text).strip()
        if not normalized:
            raise ValueError("memory text cannot be empty")

        record = MemoryRecord(
            memory_id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc).isoformat(),
            kind=str(kind),
            text=normalized,
            source=str(source),
            layer=str(layer),
            confidence=max(0.0, min(1.0, float(confidence))),
            tags=[str(tag) for tag in tags],
            metadata=dict(metadata or {}),
        )

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")

        return record

    def all(self) -> List[MemoryRecord]:
        if not self.path.exists():
            return []

        records: List[MemoryRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(MemoryRecord(**json.loads(line)))
        return records

    def recall(self, query: str, *, limit: int = 5) -> List[MemoryRecord]:
        query_tokens = self._tokens(query)
        if not query_tokens:
            return []

        scored: List[Tuple[float, MemoryRecord]] = []
        for record in self.all():
            record_tokens = self._tokens(
                " ".join(
                [
                    record.text,
                    record.layer,
                    " ".join(record.tags),
                    json.dumps(record.metadata, sort_keys=True),
                ]
                )
            )
            if not record_tokens:
                continue

            overlap = len(query_tokens & record_tokens)
            if overlap == 0:
                continue

            score = overlap / max(len(query_tokens), len(record_tokens))
            score *= max(0.0, min(1.0, record.confidence))
            scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[: max(1, int(limit))]]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", str(text).lower()))
