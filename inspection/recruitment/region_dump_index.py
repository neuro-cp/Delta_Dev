from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable


@dataclass(frozen=True)
class DumpPair:
    region: str
    baseline: Path
    post: Path
    baseline_step: int
    post_step: int


@dataclass(frozen=True)
class RegionDumpIndex:
    """
    Immutable index of region -> (baseline, post) dump paths for an episode.
    """
    episode_id: int
    pairs: Dict[str, DumpPair]

    def regions(self) -> Iterable[str]:
        return self.pairs.keys()

    def get(self, region: str) -> DumpPair:
        return self.pairs[region]

    def to_region_dumps(self) -> Dict[str, Dict[str, Path]]:
        """
        Adapter for RecruitmentMapBuilder compatibility.
        """
        out: Dict[str, Dict[str, Path]] = {}
        for region, pair in self.pairs.items():
            out[region] = {"baseline": pair.baseline, "post": pair.post}
        return out
