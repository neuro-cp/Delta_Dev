from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class HoldingBinLayout:
    """
    Conventional locations (relative to repo root):

    - holding bin: inspection/output_log_holding_bin/
    - map holder:  inspection/recruitment/recruitment_map_holder/
    """
    holding_bin_dir: Path
    map_holder_dir: Path

    @staticmethod
    def default() -> "HoldingBinLayout":
        return HoldingBinLayout(
            holding_bin_dir=Path("inspection") / "output_log_holding_bin",
            map_holder_dir=Path("inspection") / "recruitment" / "recruitment_map_holder",
        )


class HoldingBinWriter:
    """
    Writes region dump JSON payloads into the holding bin using a deterministic name.

    This is a *dumb file sink*:
    - offline-only
    - no runtime access
    - no mutation of payload (except JSON serialization)
    """

    def __init__(self, holding_bin_dir: Path) -> None:
        self._dir = Path(holding_bin_dir)

    def write_dump(
        self,
        *,
        episode_id: int,
        region: str,
        role: str,  # "baseline" or "post" (or "poke")
        step: int,
        payload: Dict[str, Any],
        tag: Optional[str] = None,
    ) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)

        safe_role = role.strip().lower().replace(" ", "_")
        safe_region = region.strip().lower().replace(" ", "_")

        tag_part = f"__tag{tag}" if tag else ""
        filename = f"ep{episode_id}__{safe_region}__{safe_role}__step{int(step)}{tag_part}.json"
        path = self._dir / filename

        # Stable serialization (sorted keys)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
        return path
