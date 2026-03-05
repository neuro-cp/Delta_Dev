from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from inspection.recruitment.region_dump_index_builder import RegionDumpIndexBuilder
from inspection.recruitment.recruitment_map_builder import RecruitmentMapBuilder
from inspection.recruitment.recruitment_map_holder import RecruitmentMapHolder


@dataclass(frozen=True)
class RecruitmentPipeline:
    """
    End-to-end offline pipeline:

    holding bin (region dumps) ->
        RegionDumpIndex ->
            RecruitmentMapBuilder ->
                RecruitmentMapHolder (persisted map)

    No runtime access. No mutation of dumps. Deterministic selection rules.
    """

    holding_bin_dir: Path
    map_holder_dir: Path

    def run(
        self,
        *,
        episode_id: int,
        episode_bounds: Dict[str, int],
        salience_summary: Dict[str, float],
        urgency_summary: Dict[str, float],
        value_summary: Dict[str, float],
        decision_summary: Optional[Dict],
        tag: Optional[str] = None,
        top_k: int = 10,
        active_threshold: float = 0.01,
    ) -> Path:

        index = RegionDumpIndexBuilder(self.holding_bin_dir).build(
            episode_id=episode_id,
            episode_bounds=episode_bounds,
            tag=tag,
        )

        rmap = RecruitmentMapBuilder(top_k=top_k, active_threshold=active_threshold).build(
            episode_id=episode_id,
            episode_bounds=episode_bounds,
            region_dumps=index.to_region_dumps(),
            salience_summary=salience_summary,
            urgency_summary=urgency_summary,
            value_summary=value_summary,
            decision_summary=decision_summary,
        )

        holder = RecruitmentMapHolder(self.map_holder_dir)
        return holder.save(rmap=rmap)
