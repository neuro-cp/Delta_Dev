from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from inspection.recruitment.holding_bin_writer import HoldingBinWriter
from inspection.recruitment.recruitment_pipeline import RecruitmentPipeline


def test_recruitment_pipeline_builds_and_persists_map(
    holding_bin_dir: Path,
    map_holder_dir: Path,
    episode_id: int,
    fake_episode_bounds: Dict[str, int],
    empty_trace_summary: Dict[str, float],
) -> None:
    writer = HoldingBinWriter(holding_bin_dir)

    # Create two regions with baseline + post
    for region in ["stn", "gpi"]:
        writer.write_dump(
            episode_id=episode_id,
            region=region,
            role="baseline",
            step=950,
            payload={
                "region": region,
                "step": 950,
                "assemblies": [
                    {"assembly_id": f"{region}:a", "output": 0.01},
                    {"assembly_id": f"{region}:b", "output": 0.00},
                ],
            },
        )
        writer.write_dump(
            episode_id=episode_id,
            region=region,
            role="post",
            step=1050,
            payload={
                "region": region,
                "step": 1050,
                "assemblies": [
                    {"assembly_id": f"{region}:a", "output": 0.20},
                    {"assembly_id": f"{region}:b", "output": 0.15},
                ],
            },
        )

    pipe = RecruitmentPipeline(holding_bin_dir=holding_bin_dir, map_holder_dir=map_holder_dir)

    out_path = pipe.run(
        episode_id=episode_id,
        episode_bounds=fake_episode_bounds,
        salience_summary=empty_trace_summary,
        urgency_summary=empty_trace_summary,
        value_summary=empty_trace_summary,
        decision_summary=None,
    )

    assert out_path.exists()

    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data["episode_id"] == episode_id
    assert "stn" in data["signatures"]
    assert "gpi" in data["signatures"]
