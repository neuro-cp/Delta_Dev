from __future__ import annotations

from inspection.recruitment.recruitment_map_builder import RecruitmentMapBuilder


def test_recruitment_map_builder_creates_map(
    fake_episode_bounds,
    fake_region_dump_index,
    empty_trace_summary,
):
    builder = RecruitmentMapBuilder()

    rmap = builder.build(
        episode_id=1,
        episode_bounds=fake_episode_bounds,
        region_dumps=fake_region_dump_index,
        salience_summary=empty_trace_summary,
        urgency_summary=empty_trace_summary,
        value_summary=empty_trace_summary,
        decision_summary=None,
    )

    assert rmap.episode_id == 1
    assert "stn" in rmap.signatures
    assert "pfc" in rmap.signatures
