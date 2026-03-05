from pathlib import Path
from inspection.recruitment.holding_bin_writer import HoldingBinWriter
from inspection.recruitment.recruitment_pipeline import RecruitmentPipeline

episode_id = 1
episode_bounds = {"start_step": 900, "end_step": 1100}
empty = {"count": 0, "mean": 0.0, "max": 0.0}

holding_bin = Path("inspection/output_log_holding_bin")
map_holder = Path("inspection/recruitment/recruitment_map_holder")

writer = HoldingBinWriter(holding_bin)

# Write baseline + post dump
writer.write_dump(
    episode_id=episode_id,
    region="stn",
    role="baseline",
    step=950,
    payload={
        "region": "stn",
        "step": 950,
        "assemblies": [
            {"assembly_id": "a", "output": 0.01},
            {"assembly_id": "b", "output": 0.00},
        ],
    },
)

writer.write_dump(
    episode_id=episode_id,
    region="stn",
    role="post",
    step=1050,
    payload={
        "region": "stn",
        "step": 1050,
        "assemblies": [
            {"assembly_id": "a", "output": 0.20},
            {"assembly_id": "b", "output": 0.15},
        ],
    },
)

pipe = RecruitmentPipeline(
    holding_bin_dir=holding_bin,
    map_holder_dir=map_holder,
)

out_path = pipe.run(
    episode_id=episode_id,
    episode_bounds=episode_bounds,
    salience_summary=empty,
    urgency_summary=empty,
    value_summary=empty,
    decision_summary=None,
)

print("Recruitment map saved to:", out_path)