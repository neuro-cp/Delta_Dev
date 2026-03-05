from engine.observation.observation_policy import ObservationPolicy


def test_policy_thresholds():
    assert ObservationPolicy.should_emit_mass_shift(0.3)
    assert not ObservationPolicy.should_emit_mass_shift(0.05)
