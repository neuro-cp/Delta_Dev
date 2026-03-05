from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest

from inspection.recruitment.region_dump_index_builder import RegionDumpIndexBuilder


def _write_dump(path: Path, *, region: str, step: int) -> None:
    path.write_text(json.dumps({
        "region": region,
        "step": step,
        "assemblies": [
            {"assembly_id": f"{region}:0", "output": 0.01},
            {"assembly_id": f"{region}:1", "output": 0.00},
        ],
    }), encoding="utf-8")


def test_region_dump_index_builder_pairs_by_role(
    holding_bin_dir: Path,
    episode_id: int,
    fake_episode_bounds: Dict[str, int],
) -> None:
    # Explicit role in filename
    _write_dump(holding_bin_dir / f"ep{episode_id}__stn__baseline__step950.json", region="stn", step=950)
    _write_dump(holding_bin_dir / f"ep{episode_id}__stn__post__step1050.json", region="stn", step=1050)

    index = RegionDumpIndexBuilder(holding_bin_dir).build(
        episode_id=episode_id,
        episode_bounds=fake_episode_bounds,
    )

    pair = index.get("stn")
    assert pair.baseline_step == 950
    assert pair.post_step == 1050


def test_region_dump_index_builder_falls_back_to_min_max_step(
    holding_bin_dir: Path,
    episode_id: int,
    fake_episode_bounds: Dict[str, int],
) -> None:
    # No explicit role tag => min step baseline, max step post
    _write_dump(holding_bin_dir / f"ep{episode_id}__pfc__x__step930.json", region="pfc", step=930)
    _write_dump(holding_bin_dir / f"ep{episode_id}__pfc__y__step1090.json", region="pfc", step=1090)

    index = RegionDumpIndexBuilder(holding_bin_dir).build(
        episode_id=episode_id,
        episode_bounds=fake_episode_bounds,
    )

    pair = index.get("pfc")
    assert pair.baseline_step == 930
    assert pair.post_step == 1090
