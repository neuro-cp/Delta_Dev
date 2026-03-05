from integration.substrate_surface.confidence_weighting_policy import ConfidenceWeightingPolicy


def test_confidence_attenuates():
    magnitude = 1.0
    confidence = 0.5

    adjusted = ConfidenceWeightingPolicy.apply(magnitude, confidence)

    assert adjusted == 0.5


def test_confidence_never_amplifies():
    magnitude = 0.6
    confidence = 1.5  # should be clamped

    adjusted = ConfidenceWeightingPolicy.apply(magnitude, confidence)

    assert adjusted <= magnitude
