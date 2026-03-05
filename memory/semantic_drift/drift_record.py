from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

### is_persistent → temporal_persistence
###density → structural_density

@dataclass(frozen=True)
class DriftRecord:
    """
    Immutable, offline diagnostic record describing semantic stability or drift.

    This record is:
    - derived from semantic records only
    - descriptive, not prescriptive
    - non-authoritative
    - safe to discard and recompute

    DriftRecords MUST NEVER influence runtime behavior.
    """

    # Identity
    semantic_type: str
    window_start_episode: int
    window_end_episode: int

    # Occurrence metrics
    total_occurrences: int
    unique_episode_count: int

    # Temporal behavior
    first_seen_episode: int
    last_seen_episode: int
    persistence_span: int  # last_seen - first_seen

    # Novelty & stability flags (diagnostic only)
    is_novel: bool
    is_recurrent: bool
    is_persistent: bool

    # Optional descriptive statistics
    frequency_per_episode: Optional[float]
    density: Optional[float]

    # Metadata (non-executive)
    policy_version: str
    schema_version: str

    tags: Dict[str, Any] = field(default_factory=dict)
