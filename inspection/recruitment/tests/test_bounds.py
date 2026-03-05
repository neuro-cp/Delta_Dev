def test_region_dump_index_respects_episode_bounds(
    holding_bin_dir,
    episode_id,
):
    from inspection.recruitment.region_dump_index_builder import RegionDumpIndexBuilder
    import json

    # Write two dumps OUTSIDE bounds
    (holding_bin_dir / f"ep{episode_id}__stn__baseline__step100.json").write_text(json.dumps({
        "region": "stn",
        "step": 100,
        "assemblies": [],
    }))

    (holding_bin_dir / f"ep{episode_id}__stn__post__step2000.json").write_text(json.dumps({
        "region": "stn",
        "step": 2000,
        "assemblies": [],
    }))

    builder = RegionDumpIndexBuilder(holding_bin_dir)

    import pytest
    with pytest.raises(ValueError):
        builder.build(
            episode_id=episode_id,
            episode_bounds={"start_step": 900, "end_step": 1100},
        )