from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from inspection.recruitment.recruitment_map import RecruitmentMap


@dataclass(frozen=True)
class RecruitmentMapHolder:
    """
    File-based persistence for RecruitmentMap artifacts.
    Output is inspection-only; no runtime edges.

    Convention: store maps under inspection/recruitment/recruitment_map_holder/
    """

    root_dir: Path

    def save(
        self,
        *,
        rmap: RecruitmentMap,
        filename: Optional[str] = None,
    ) -> Path:
        out_dir = Path(self.root_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = f"recruitment_map__ep{rmap.episode_id}.json"

        path = out_dir / filename
        path.write_text(json.dumps(rmap.to_dict(), sort_keys=True, indent=2), encoding="utf-8")
        return path
