from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from inspection.recruitment.recruitment_stats_from_dump import load_dump
from inspection.recruitment.region_dump_index import DumpPair, RegionDumpIndex


_EP_RE = re.compile(r"^ep(?P<ep>\d+)__")
_ROLE_RE = re.compile(r"__(?P<role>baseline|post|poke)__", flags=re.IGNORECASE)
_STEP_RE = re.compile(r"__step(?P<step>\d+)", flags=re.IGNORECASE)


@dataclass(frozen=True)
class RegionDumpIndexBuilder:
    """
    Builds a RegionDumpIndex by scanning a holding-bin folder for JSON dumps.

    Deterministic rules:
    - prefer explicit role-tagged files ("baseline" vs "post"/"poke")
    - otherwise choose min-step as baseline and max-step as post
    - constrain to episode_bounds if provided
    """

    holding_bin_dir: Path

    def build(
        self,
        *,
        episode_id: int,
        episode_bounds: Optional[Dict[str, int]] = None,
        tag: Optional[str] = None,
    ) -> RegionDumpIndex:

        root = Path(self.holding_bin_dir)
        if not root.exists():
            raise FileNotFoundError(f"Holding bin directory not found: {root}")

        candidates = [p for p in root.glob("*.json") if p.is_file()]
        if not candidates:
            raise ValueError(f"No JSON dumps found in holding bin: {root}")

        # Filter by episode id (prefer name, fallback to payload)
        filtered: List[Path] = []
        for p in candidates:
            m = _EP_RE.match(p.name)
            if m and int(m.group("ep")) == int(episode_id):
                filtered.append(p)
                continue
            # Fallback: allow files without ep prefix but with payload match
            try:
                payload = load_dump(p)
            except Exception:
                continue
            if int(payload.get("episode_id", -1)) == int(episode_id):
                filtered.append(p)

        if not filtered:
            raise ValueError(f"No dumps matched episode_id={episode_id} in {root}")

        # Optional tag filter (filename tag only; deterministic and cheap)
        if tag:
            filtered = [p for p in filtered if f"__tag{tag}" in p.name]
            if not filtered:
                raise ValueError(f"No dumps matched episode_id={episode_id} and tag={tag} in {root}")

        # Group by region
        by_region: Dict[str, List[Tuple[Path, Dict]]] = {}
        for p in filtered:
            payload = load_dump(p)
            region = str(payload.get("region", "")).lower()
            step = int(payload.get("step", -1))

            if episode_bounds is not None:
                start = int(episode_bounds["start_step"])
                end = int(episode_bounds["end_step"])
                if step < start or step > end:
                    continue

            by_region.setdefault(region, []).append((p, payload))

        if not by_region:
            raise ValueError("All dumps were filtered out by episode_bounds (or missing region/step).")

        pairs: Dict[str, DumpPair] = {}

        for region, items in sorted(by_region.items(), key=lambda kv: kv[0]):
            # Identify explicit roles from filenames if possible
            baseline_items: List[Tuple[Path, Dict]] = []
            post_items: List[Tuple[Path, Dict]] = []
            other_items: List[Tuple[Path, Dict]] = []

            for p, payload in items:
                role_m = _ROLE_RE.search(p.name)
                if role_m:
                    role = role_m.group("role").lower()
                    if role == "baseline":
                        baseline_items.append((p, payload))
                    else:
                        post_items.append((p, payload))
                else:
                    other_items.append((p, payload))

            def _best_by_step(it: List[Tuple[Path, Dict]], *, pick_max: bool) -> Tuple[Path, Dict]:
                # deterministic tiebreaker: step then filename
                sorted_it = sorted(
                    it,
                    key=lambda t: (int(t[1].get("step", -1)), t[0].name),
                    reverse=pick_max,
                )
                return sorted_it[0]

            if baseline_items and post_items:
                b_path, b_payload = _best_by_step(baseline_items, pick_max=False)
                p_path, p_payload = _best_by_step(post_items, pick_max=True)
            else:
                # Step-based fallback across all items
                if len(items) < 2:
                    raise ValueError(f"Region '{region}' has <2 dumps; cannot form baseline/post pair.")
                b_path, b_payload = _best_by_step(items, pick_max=False)
                p_path, p_payload = _best_by_step(items, pick_max=True)

            b_step = int(b_payload.get("step", -1))
            p_step = int(p_payload.get("step", -1))

            if b_step == p_step and b_path == p_path:
                raise ValueError(f"Region '{region}' baseline and post resolved to the same dump: {b_path.name}")

            pairs[region] = DumpPair(
                region=region,
                baseline=b_path,
                post=p_path,
                baseline_step=b_step,
                post_step=p_step,
            )

        return RegionDumpIndex(episode_id=int(episode_id), pairs=pairs)
