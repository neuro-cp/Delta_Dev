from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class RecruitmentSignature:
    """
    Immutable, inspection-only snapshot describing *recruitment mechanics*
    for a single region over a baseline→post comparison window.

    This encodes *structure*, not meaning.

    Lawful uses:
    - compare signatures
    - aggregate signatures into maps
    - correlate with offline cognition/semantics/outcomes

    NOT lawful:
    - drive runtime behavior
    - encode actions or rules
    - introduce authority edges
    """

    # -------------------------
    # Episodic identity / scope
    # -------------------------

    episode_id: int
    region: str

    episode_start_step: int
    episode_end_step: int

    # -------------------------
    # Inert context summaries (optional)
    # -------------------------

    salience_summary: Dict[str, float]
    urgency_summary: Dict[str, float]
    value_summary: Dict[str, float]

    decision_summary: Optional[Dict]
    has_decision: bool
    winner: Optional[str]

    # -------------------------
    # Comparison window
    # -------------------------

    baseline_step: int
    post_step: int

    # -------------------------
    # Recruitment comparison
    # -------------------------

    baseline_mass: float
    post_mass: float
    delta_mass: float

    baseline_fraction_active: float
    post_fraction_active: float
    delta_fraction_active: float

    baseline_tiers: Dict[str, int]
    post_tiers: Dict[str, int]

    top_k_overlap: float

    # -------------------------
    # Structural interpretation labels
    # -------------------------

    recruitment_level: str        # none|partial|full|suppression
    identity_stability: str       # stable|shifted|reorganized
    scaling_direction: str        # up|down|flat
