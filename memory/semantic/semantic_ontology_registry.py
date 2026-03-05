from __future__ import annotations

from enum import Enum


class SemanticOntology(str, Enum):
    """
    Canonical semantic ontology terms.

    This registry is:
    - passive
    - inert
    - non-authoritative
    - string-stable

    It exists solely to prevent semantic drift
    and uncontrolled vocabulary growth.

    Removing this file must not change behavior.
    """

    # Structural
    STRUCTURAL_FREQUENCY = "structural_frequency"
    STRUCTURAL_DENSITY = "structural_density"
    STRUCTURAL_CO_OCCURRENCE = "structural_co_occurrence"
    STRUCTURAL_SIMILARITY = "structural_similarity"

    # Temporal
    TEMPORAL_PERSISTENCE = "temporal_persistence"
    TEMPORAL_RECURRENCE = "temporal_recurrence"
    TEMPORAL_SPAN = "temporal_span"
    TEMPORAL_TRANSITION = "temporal_transition"

    # Decision-related (descriptive only)
    DECISION_PRESENCE = "decision_presence"
    DECISION_MULTIPLICITY = "decision_multiplicity"
    DECISION_SILENCE = "decision_silence"

    # Stability / Drift
    STABILITY_CONSISTENT = "stability_consistent"
    STABILITY_VARIABLE = "stability_variable"
    STABILITY_NOVEL = "stability_novel"
