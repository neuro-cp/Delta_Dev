from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from inspection.recruitment.recruitment_map import RecruitmentMap
from inspection.recruitment.recruitment_signature import RecruitmentSignature
from inspection.recruitment.recruitment_signature_builder import RecruitmentSignatureBuilder


class RecruitmentMapBuilder:
    """
    Orchestrates per-region RecruitmentSignature construction into a single
    episode-scoped RecruitmentMap.

    Inputs are *offline dumps* (baseline/post) per region.
    """

    def __init__(self, *, top_k: int = 10, active_threshold: float = 0.01) -> None:
        self._sig_builder = RecruitmentSignatureBuilder(top_k=top_k, active_threshold=active_threshold)

    def build(
        self,
        *,
        episode_id: int,
        episode_bounds: Dict[str, int],
        region_dumps: Dict[str, Dict[str, Path]],
        salience_summary: Dict[str, float],
        urgency_summary: Dict[str, float],
        value_summary: Dict[str, float],
        decision_summary: Optional[Dict],
    ) -> RecruitmentMap:

        signatures: Dict[str, RecruitmentSignature] = {}

        for region, dumps in region_dumps.items():
            sig = self._sig_builder.build(
                episode_id=episode_id,
                region=region,
                baseline_dump=dumps["baseline"],
                post_dump=dumps["post"],
                episode_bounds=episode_bounds,
                salience_summary=salience_summary,
                urgency_summary=urgency_summary,
                value_summary=value_summary,
                decision_summary=decision_summary,
            )
            signatures[region] = sig

        return RecruitmentMap(
            episode_id=episode_id,
            signatures=signatures,
        )
