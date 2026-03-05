def test_recruitment_pipeline_is_deterministic(
    holding_bin_dir,
    map_holder_dir,
    episode_id,
    fake_episode_bounds,
    empty_trace_summary,
):
    from inspection.recruitment.holding_bin_writer import HoldingBinWriter
    from inspection.recruitment.recruitment_pipeline import RecruitmentPipeline
    import json

    writer = HoldingBinWriter(holding_bin_dir)

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
                ],
            },
        )

    pipe = RecruitmentPipeline(
        holding_bin_dir=holding_bin_dir,
        map_holder_dir=map_holder_dir,
    )

    out1 = pipe.run(
        episode_id=episode_id,
        episode_bounds=fake_episode_bounds,
        salience_summary=empty_trace_summary,
        urgency_summary=empty_trace_summary,
        value_summary=empty_trace_summary,
        decision_summary=None,
    )

    data1 = json.loads(out1.read_text())

    # Run again
    out2 = pipe.run(
        episode_id=episode_id,
        episode_bounds=fake_episode_bounds,
        salience_summary=empty_trace_summary,
        urgency_summary=empty_trace_summary,
        value_summary=empty_trace_summary,
        decision_summary=None,
    )

    data2 = json.loads(out2.read_text())

    assert data1 == data2