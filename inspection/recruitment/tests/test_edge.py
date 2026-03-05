def test_signature_detects_suppression(
    episode_id,
    fake_episode_bounds,
    empty_trace_summary,
    tmp_path,
):
    from inspection.recruitment.recruitment_signature_builder import RecruitmentSignatureBuilder
    import json

    baseline = tmp_path / "baseline.json"
    post = tmp_path / "post.json"

    baseline.write_text(json.dumps({
        "region": "stn",
        "step": 950,
        "assemblies": [
            {"assembly_id": "a", "output": 0.5},
        ],
    }))

    post.write_text(json.dumps({
        "region": "stn",
        "step": 1050,
        "assemblies": [
            {"assembly_id": "a", "output": 0.01},
        ],
    }))

    builder = RecruitmentSignatureBuilder()

    sig = builder.build(
        episode_id=episode_id,
        region="stn",
        baseline_dump=baseline,
        post_dump=post,
        episode_bounds=fake_episode_bounds,
        salience_summary=empty_trace_summary,
        urgency_summary=empty_trace_summary,
        value_summary=empty_trace_summary,
        decision_summary=None,
    )

    assert sig.recruitment_level == "suppression"
    assert sig.scaling_direction == "down"