from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class SemanticAnnotationRecord:
    """
    Immutable, offline annotation applied to a closed episode.

    An annotation is descriptive metadata only.
    It carries NO authority and is never consulted by runtime logic.
    """

    # --------------------------------------------------
    # Identity
    # --------------------------------------------------

    annotation_id: str
    episode_id: int

    # --------------------------------------------------
    # Classification
    # --------------------------------------------------

    annotation_type: str

    # --------------------------------------------------
    # Provenance
    # --------------------------------------------------

    source_semantic_ids: List[str]
    policy_version: str
    schema_version: str

    # --------------------------------------------------
    # Temporal guarantees
    # --------------------------------------------------

    applied_during_replay: bool
    episode_closed: bool

    # --------------------------------------------------
    # Annotation payload
    # --------------------------------------------------

    descriptor: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    confidence: Optional[float] = None

    # --------------------------------------------------
    # Optional tags / notes
    # --------------------------------------------------

    tags: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None
