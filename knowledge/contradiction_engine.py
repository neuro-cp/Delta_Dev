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
    STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "can",
        "for",
        "from",
        "if",
        "in",
        "is",
        "it",
        "of",
        "or",
        "that",
        "the",
        "then",
        "this",
        "to",
        "with",
    }

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
        candidate_core = self._content_tokens(candidate_tokens)
        candidate_negated = bool(candidate_tokens & self.NEGATORS)

        for record in existing:
            if record.concept_id == candidate.concept_id:
                continue
            tokens = self._tokens(record.definition)
            record_core = self._content_tokens(tokens)
            if not tokens:
                continue

            shared = len(candidate_core & record_core)
            if shared < 3:
                continue
            overlap_ratio = shared / max(1, min(len(candidate_core), len(record_core)))
            if overlap_ratio < 0.5:
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
                    metadata={
                        "shared_token_count": shared,
                        "content_overlap_ratio": round(overlap_ratio, 4),
                    },
                )
            )

        return records

    def add_all(self, records: List[ContradictionRecord]) -> List[ContradictionRecord]:
        if not records:
            return []

        existing_pairs = {
            self._pair_key(record.claim_a_id, record.claim_b_id, record.status)
            for record in self.latest()
        }
        unique: List[ContradictionRecord] = []
        for record in records:
            key = self._pair_key(record.claim_a_id, record.claim_b_id, record.status)
            if key in existing_pairs:
                continue
            existing_pairs.add(key)
            unique.append(record)
        if not unique:
            return []

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            for record in unique:
                handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return unique

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

    def latest(self) -> List[ContradictionRecord]:
        records_by_id: dict[str, ContradictionRecord] = {}
        for record in self.all():
            records_by_id[record.contradiction_id] = record
        return list(records_by_id.values())

    def resolve(
        self,
        contradiction: ContradictionRecord,
        *,
        resolution: str,
        evidence_ids: List[str],
        rationale: str,
        severity: float | None = None,
    ) -> ContradictionRecord:
        """
        Append a resolved contradiction revision without deleting either claim.
        """
        revised = ContradictionRecord(
            contradiction_id=contradiction.contradiction_id,
            created_at=contradiction.created_at,
            claim_a_id=contradiction.claim_a_id,
            claim_b_id=contradiction.claim_b_id,
            reason=contradiction.reason,
            severity=max(0.0, min(1.0, float(severity if severity is not None else contradiction.severity))),
            status="resolved",
            resolution=str(resolution),
            resolved_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                **contradiction.metadata,
                "resolution_evidence_ids": list(dict.fromkeys(evidence_ids)),
                "resolution_rationale": str(rationale),
                "resolution_method": "append_only_resolution_v1",
            },
        )
        self.add_all([revised])
        return revised

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_']+", str(text).lower()))

    @classmethod
    def _content_tokens(cls, tokens: set[str]) -> set[str]:
        return {
            token
            for token in tokens
            if token not in cls.NEGATORS
            and token not in cls.STOPWORDS
            and len(token) > 2
        }

    @staticmethod
    def _pair_key(claim_a_id: str, claim_b_id: str, status: str) -> tuple[str, str, str]:
        left, right = sorted((str(claim_a_id), str(claim_b_id)))
        return (left, right, str(status))
