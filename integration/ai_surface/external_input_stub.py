# integration/ai_surface/external_input_stub.py

from typing import Dict, Any

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.ai_surface.ai_model_interface import ExternalModelInterface


class ExternalInputStub(ExternalModelInterface):
    """
    Deterministic in-process stub for external AI integration.

    Purpose:
    - Simulates an external model producing AIOutputBundle
    - Allows integration testing without transport
    - Produces immutable advisory output
    - Contains zero substrate access
    - Contains zero execution authority

    Contract:
    - Deterministic
    - Pure
    - No runtime coupling
    - No memory coupling
    - No side effects
    """

    def produce_output(self, input_payload: Dict[str, Any]) -> AIOutputBundle:
        """
        Generate a fixed advisory bundle based on input.

        This stub intentionally ignores most dynamic behavior.
        It exists to validate the integration boundary only.
        """

        semantic_tokens = input_payload.get("semantic_tokens", ["default_signal"])
        quantitative_fields = input_payload.get("quantitative_fields", {})

        # We do NOT interpret these.
        # We simply wrap them in an advisory envelope.

        return AIOutputBundle(
            role="strategic_defense_advisor",
            mode="active",
            payload={
                "semantic_tokens": semantic_tokens,
                "quantitative_fields": quantitative_fields,
            },
            confidence_band=0.75,
        )