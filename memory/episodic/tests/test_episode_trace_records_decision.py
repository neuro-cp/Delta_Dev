from __future__ import annotations

from memory.episodic.episode_trace import EpisodeTrace
from memory.episodic.episode_tracker import EpisodeTracker


def _get_active_episode(tracker):
    """
    Compatibility accessor:
    - supports tracker.active_episode (attribute/property)
    - supports tracker.active_episode() (method)
    """
    ae = getattr(tracker, "active_episode", None)
    if callable(ae):
        return ae()
    return ae


def _start_episode(tracker, *, step: int, reason: str):
    """
    Compatibility shim:
    - some tracker versions want time=...
    - some don't
    """
    try:
        return tracker.start_episode(step=step, time=0.0, reason=reason)
    except TypeError:
        return tracker.start_episode(step=step, reason=reason)


def _mark_decision(tracker, *, step: int, winner: str):
    """
    Compatibility shim:
    - some tracker versions want time=...
    - some don't
    - some accept confidence, some don't
    """
    try:
        return tracker.mark_decision(step=step, time=0.0, winner=winner, confidence=0.9)
    except TypeError:
        try:
            return tracker.mark_decision(step=step, time=0.0, winner=winner)
        except TypeError:
            try:
                return tracker.mark_decision(step=step, winner=winner, confidence=0.9)
            except TypeError:
                return tracker.mark_decision(step=step, winner=winner)


def main() -> None:
    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace)

    _start_episode(tracker, step=0, reason="test_start")

    ep = _get_active_episode(tracker)
    assert ep is not None, "Expected an active episode after start_episode()"

    first_id = getattr(ep, "episode_id", None)
    assert first_id is not None, "Active episode missing episode_id"

    _mark_decision(tracker, step=10, winner="D2")

    # Now verify trace includes a decision record.
    # NOTE: If your EpisodeTrace currently only logs start/close,
    # this assert will fail next, which is the *real* contract gap we want.
    recs = trace.records()

    hit = [
        r for r in recs
        if getattr(r, "event", None) == "decision"
        and getattr(r, "episode_id", None) == first_id
        and getattr(r, "step", None) == 10
        and getattr(r, "payload", {}).get("winner") == "D2"
    ]

    assert hit, f"Expected decision trace record; got events={[getattr(r,'event',None) for r in recs]}"
    print("PASS: test_episode_trace_records_decision")


if __name__ == "__main__":
    main()
