from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SemanticProvenance:
    """
    Traceability metadata for a semantic record.

    Provenance ensures semantic memory never bypasses
    episodic or consolidation structure.
    """

    episode_ids: List[int]
    consolidation_ids: Optional[List[int]] = None
    sample_size: int = 0


@dataclass(frozen=True)
class SemanticTemporalScope:
    """
    Temporal bounds over which a semantic pattern
    has been observed.
    """

    first_observed_step: int
    last_observed_step: int
    observation_window: int


@dataclass(frozen=True)
class SemanticStatistics:
    """
    Descriptive statistics only.

    No value, salience, reward, or preference
    may appear here.
    """

    count: int
    frequency: Optional[float] = None
    distributions: Optional[Dict[str, Any]] = None
    confidence_intervals: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class SemanticStability:
    """
    Stability characteristics of a semantic pattern.

    Used for decay and persistence decisions offline.
    """

    support: float
    variance: Optional[float] = None
    decay_rate: Optional[float] = None


@dataclass(frozen=True)
class SemanticRecord:
    """
    Immutable semantic memory record.

    This is a passive, offline-produced artifact.
    It carries NO authority and is never consulted
    directly by runtime decision logic.
    """

    # Identity & versioning
    semantic_id: str
    policy_version: str
    schema_version: str

    # Provenance & scope
    provenance: SemanticProvenance
    temporal_scope: SemanticTemporalScope

    # Pattern description
    pattern_type: str
    pattern_descriptor: Any

    # Statistics & stability
    statistics: SemanticStatistics
    stability: SemanticStability

    # Descriptive metadata
    tags: Dict[str, Any] = field(default_factory=dict)

    # Optional human-readable notes
    notes: Optional[str] = None
