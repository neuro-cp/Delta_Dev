from __future__ import annotations

from pathlib import Path
from typing import Dict

from inspection.recruitment.recruitment_signature_builder import RecruitmentSignatureBuilder
from inspection.recruitment.recruitment_signature import RecruitmentSignature


def test_recruitment_signature_builder_creates_signature(
    episode_id: int,
    fake_episode_bounds: Dict[str, int],
    recruitment_dump_paths: Dict[str, Path],
    empty_trace_summary: Dict[str, float],
) -> None:
    builder = RecruitmentSignatureBuilder(top_k=10, active_threshold=0.01)

    sig = builder.build(
        episode_id=episode_id,
        region="stn",
        baseline_dump=recruitment_dump_paths["baseline"],
        post_dump=recruitment_dump_paths["post"],
        episode_bounds=fake_episode_bounds,
        salience_summary=empty_trace_summary,
        urgency_summary=empty_trace_summary,
        value_summary=empty_trace_summary,
        decision_summary=None,
    )

    assert isinstance(sig, RecruitmentSignature)

    assert sig.episode_id == episode_id
    assert sig.region == "stn"

    assert sig.recruitment_level == "full"
    assert sig.identity_stability in ("stable", "shifted", "reorganized")
    assert sig.scaling_direction == "up"

    assert sig.delta_fraction_active > 0.5
    assert sig.delta_mass > 1.0
    assert 0.9 <= sig.top_k_overlap <= 1.0

    assert sig.has_decision is False
    assert sig.winner is None
