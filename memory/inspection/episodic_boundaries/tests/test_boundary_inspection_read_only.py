from memory.episodic.episode_trace import EpisodeTrace
from memory.inspection.episodic_boundaries.boundary_inspection_adapter import inspect_boundaries


def test_boundary_inspection_is_read_only():
    trace = EpisodeTrace()
    trace.record_start(episode_id=0, step=0)
    trace.record_close(episode_id=0, step=5)

    report = inspect_boundaries(trace)

    assert len(report.episodes) == 1
    assert len(report.records) == 2

    # Ensure original trace untouched
    assert len(trace.records()) == 2
