from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import List

from knowledge.semantic_record import SemanticKnowledgeRecord


class SemanticKnowledgeStore:
    """
    Append-only semantic knowledge store.

    Newer records may reference prior records in revision_history. History is
    preserved instead of overwritten.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def add(self, record: SemanticKnowledgeRecord) -> SemanticKnowledgeRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record

    def all(self) -> List[SemanticKnowledgeRecord]:
        if not self.path.exists():
            return []

        records: List[SemanticKnowledgeRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(SemanticKnowledgeRecord(**json.loads(line)))
        return records

    def latest(self) -> List[SemanticKnowledgeRecord]:
        records = self.all()
        superseded = {
            prior_id
            for record in records
            for prior_id in record.revision_history
        }
        return [record for record in records if record.concept_id not in superseded]

    def find_related(self, text: str, *, threshold: float = 0.55) -> List[SemanticKnowledgeRecord]:
        query_tokens = self._tokens(text)
        if not query_tokens:
            return []

        matches = []
        for record in self.latest():
            record_tokens = self._tokens(record.concept + " " + record.definition)
            if not record_tokens:
                continue
            overlap = len(query_tokens & record_tokens)
            score = overlap / max(len(query_tokens), len(record_tokens))
            if score >= threshold:
                matches.append(record)
        return matches

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]+", str(text).lower()))
