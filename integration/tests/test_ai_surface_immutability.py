from integration.ai_surface.ai_output_bundle import AIOutputBundle
import pytest

def test_ai_output_bundle_is_immutable():
    bundle = AIOutputBundle(
        role="strategic_defense_advisor",
        mode="active",
        payload={"x": 1},
        confidence_band=0.9,
    )

    with pytest.raises(Exception):
        bundle.role = "mutate"
