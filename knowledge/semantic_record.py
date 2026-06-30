from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SemanticKnowledgeRecord:
    """
    Consolidated semantic knowledge.

    Knowledge evolves. Source experience remains immutable.
    """

    concept_id: str
    created_at: str
    updated_at: str
    concept: str
    definition: str
    confidence: float
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    relationship_ids: List[str] = field(default_factory=list)
    creation_source: str = ""
    last_validation: str | None = None
    revision_history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
