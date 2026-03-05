from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture
def episode_id() -> int:
    return 42


@pytest.fixture
def fake_episode_bounds() -> Dict[str, int]:
    return {"start_step": 900, "end_step": 1100}


@pytest.fixture
def empty_trace_summary() -> Dict[str, float]:
    return {"count": 0, "mean": 0.0, "max": 0.0}


@pytest.fixture
def holding_bin_dir(tmp_path: Path) -> Path:
    d = tmp_path / "inspection" / "output_log_holding_bin"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def map_holder_dir(tmp_path: Path) -> Path:
    d = tmp_path / "inspection" / "recruitment" / "recruitment_map_holder"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def recruitment_dump_paths(tmp_path: Path) -> Dict[str, Path]:
    baseline = tmp_path / "baseline.json"
    post = tmp_path / "post.json"

    baseline.write_text(json.dumps({
        "region": "stn",
        "step": 948,
        "assemblies": [
            {"assembly_id": f"stn:{i}", "output": 0.01 if i < 8 else 0.0}
            for i in range(25)
        ],
    }), encoding="utf-8")

    post.write_text(json.dumps({
        "region": "stn",
        "step": 1051,
        "assemblies": [
            {"assembly_id": f"stn:{i}", "output": 0.22 if i < 8 else 0.11}
            for i in range(25)
        ],
    }), encoding="utf-8")

    return {"baseline": baseline, "post": post}


@pytest.fixture
def fake_region_dump_index(tmp_path: Path) -> Dict[str, Dict[str, Path]]:
    regions = {}
    for region in ["stn", "gpi", "pfc"]:
        baseline = tmp_path / f"{region}_baseline.json"
        post = tmp_path / f"{region}_post.json"

        baseline.write_text(json.dumps({
            "region": region,
            "step": 950,
            "assemblies": [
                {"assembly_id": f"{region}:a", "output": 0.01},
                {"assembly_id": f"{region}:b", "output": 0.00},
            ],
        }), encoding="utf-8")

        post.write_text(json.dumps({
            "region": region,
            "step": 1050,
            "assemblies": [
                {"assembly_id": f"{region}:a", "output": 0.20},
                {"assembly_id": f"{region}:b", "output": 0.15},
            ],
        }), encoding="utf-8")

        regions[region] = {"baseline": baseline, "post": post}
    return regions
