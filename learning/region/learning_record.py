from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class SemanticCandidate:
    text: str
    evidence_memory_ids: List[str]
    confidence: float
    rationale: str


@dataclass(frozen=True)
class ConfidenceUpdate:
    target_id: str
    delta: float
    reason: str


@dataclass(frozen=True)
class LearningRecord:
    """
    Durable, non-authoritative learning output.

    Learning records describe possible knowledge evolution. They do not mutate
    memory, goals, routing, execution, or runtime state.
    """

    learning_id: str
    created_at: str
    cycle_id: str
    semantic_candidates: List[SemanticCandidate] = field(default_factory=list)
    confidence_updates: List[ConfidenceUpdate] = field(default_factory=list)
    questions: List[str] = field(default_factory=list)
    goal_candidates: List[str] = field(default_factory=list)
    consolidation_candidates: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
