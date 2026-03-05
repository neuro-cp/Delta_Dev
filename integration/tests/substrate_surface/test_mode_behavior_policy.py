from integration.substrate_surface.mode_behavior_policy import ModeBehaviorPolicy


def test_mode_clamps_magnitude():
    magnitude = 0.9

    clamped = ModeBehaviorPolicy.apply("passive", magnitude)

    assert clamped == 0.25
