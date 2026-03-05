from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from inspection.recruitment.recruitment_signature import RecruitmentSignature
from inspection.recruitment.recruitment_stats_from_dump import (
    load_dump,
    total_mass,
    fraction_active,
    top_k_assemblies,
    tier_counts,
    overlap_fraction,
    DEFAULT_ACTIVE_THRESHOLD,
)


class RecruitmentSignatureBuilder:
    """
    Builds episode-scoped RecruitmentSignature objects by comparing
    a baseline dump vs a post dump for a region.

    This performs *interpretation of mechanics* (recruitment vs scaling)
    based on measurable structure.

    Offline-only. Read-only. No caching.
    """

    def __init__(self, *, top_k: int = 10, active_threshold: float = DEFAULT_ACTIVE_THRESHOLD) -> None:
        self._top_k = int(top_k)
        self._active_threshold = float(active_threshold)

    def build(
        self,
        *,
        episode_id: int,
        region: str,
        baseline_dump: Path,
        post_dump: Path,
        episode_bounds: Dict[str, int],
        salience_summary: Dict[str, float],
        urgency_summary: Dict[str, float],
        value_summary: Dict[str, float],
        decision_summary: Optional[Dict],
    ) -> RecruitmentSignature:

        base = load_dump(baseline_dump)
        post = load_dump(post_dump)

        base_asm = list(base.get("assemblies", []))
        post_asm = list(post.get("assemblies", []))

        base_mass = total_mass(base_asm)
        post_mass = total_mass(post_asm)

        base_frac = fraction_active(base_asm, threshold=self._active_threshold)
        post_frac = fraction_active(post_asm, threshold=self._active_threshold)

        base_top = top_k_assemblies(base_asm, self._top_k)
        post_top = top_k_assemblies(post_asm, self._top_k)

        overlap = overlap_fraction(base_top, post_top)

        # -------------------------
        # Structural interpretation
        # -------------------------

        if post_frac >= 0.95 and base_frac < 0.95:
            recruitment_level = "full"
        elif post_frac > base_frac and post_frac >= 0.3:
            recruitment_level = "partial"
        elif post_frac < base_frac:
            recruitment_level = "suppression"
        else:
            recruitment_level = "none"

        if overlap >= 0.8:
            identity_stability = "stable"
        elif overlap >= 0.3:
            identity_stability = "shifted"
        else:
            identity_stability = "reorganized"

        if post_mass > base_mass:
            scaling_direction = "up"
        elif post_mass < base_mass:
            scaling_direction = "down"
        else:
            scaling_direction = "flat"

        has_decision = decision_summary is not None
        winner = decision_summary.get("winner") if decision_summary else None

        return RecruitmentSignature(
            episode_id=int(episode_id),
            region=str(region),

            episode_start_step=int(episode_bounds["start_step"]),
            episode_end_step=int(episode_bounds["end_step"]),

            salience_summary=dict(salience_summary),
            urgency_summary=dict(urgency_summary),
            value_summary=dict(value_summary),

            decision_summary=dict(decision_summary) if decision_summary else None,
            has_decision=bool(has_decision),
            winner=str(winner) if winner is not None else None,

            baseline_step=int(base.get("step", -1)),
            post_step=int(post.get("step", -1)),

            baseline_mass=float(base_mass),
            post_mass=float(post_mass),
            delta_mass=float(post_mass - base_mass),

            baseline_fraction_active=float(base_frac),
            post_fraction_active=float(post_frac),
            delta_fraction_active=float(post_frac - base_frac),

            baseline_tiers=tier_counts(base_asm),
            post_tiers=tier_counts(post_asm),

            top_k_overlap=float(overlap),

            recruitment_level=str(recruitment_level),
            identity_stability=str(identity_stability),
            scaling_direction=str(scaling_direction),
        )
