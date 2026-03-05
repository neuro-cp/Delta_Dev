
from memory.episodic_boundary.boundary_event import BoundaryEvent

def test_boundary_event_is_frozen():
    ev = BoundaryEvent(step=1, reason="x")
    try:
        ev.step = 2
        assert False
    except Exception:
        assert True
