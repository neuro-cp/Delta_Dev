from integration.ai_surface.ai_confidence_band import ConfidenceBand

def test_confidence_band_structure():
    band = ConfidenceBand(center=0.8, width=0.05)
    assert band.center == 0.8
    assert band.width == 0.05
