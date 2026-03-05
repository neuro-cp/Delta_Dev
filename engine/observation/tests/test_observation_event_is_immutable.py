from engine.observation.observation_event import ObservationEvent
import pytest


def test_observation_event_is_immutable():
    ev = ObservationEvent(step=1, region="stn", event_type="mass", payload={})
    with pytest.raises(Exception):
        ev.step = 2
