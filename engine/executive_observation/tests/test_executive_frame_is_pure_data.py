
from engine.executive_observation.executive_frame import ExecutiveFrame

def test_executive_frame_is_pure():
    f = ExecutiveFrame(step=1, episode_id=None, observations={})
    assert f.step == 1
