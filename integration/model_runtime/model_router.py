"""
integration/model_runtime/model_router.py

Deliberative model routing controller.

Responsibilities
----------------
• Execute models in deterministic order
• Pass reasoning forward between models
• Allow critique and refinement stages
• Stop escalation once confidence threshold is met
• Never interact with GPU directly
• Use GGUFModelRunner as execution backend
"""

from typing import Dict, Any, List

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.model_runtime.gguf_model_runner import GGUFModelRunner


class ModelRouter:
    """
    Deterministic deliberative multi-model router.
    """

    # -----------------------------------------------------
    # Escalation chain
    # -----------------------------------------------------

    ROUTE_CHAIN: List[str] = [
        "phi3",   # initial reasoning attempt
        "phi4",   # critique / improvement
        "qwen",   # deeper analysis
        "llama",  # final verification
    ]

    # -----------------------------------------------------
    # Confidence threshold
    # -----------------------------------------------------

    CONFIDENCE_THRESHOLD: float = 0.95

    # -----------------------------------------------------
    # Initialization
    # -----------------------------------------------------

    def __init__(self) -> None:

        self.runners: Dict[str, GGUFModelRunner] = {
            model_name: GGUFModelRunner(model_name)
            for model_name in self.ROUTE_CHAIN
        }

    # -----------------------------------------------------
    # Routing logic
    # -----------------------------------------------------

    def route(self, input_payload: Dict[str, Any]) -> AIOutputBundle:
        """
        Execute the reasoning chain.
        Each model receives the previous model's output.
        """

        context_payload = dict(input_payload)
        last_result: AIOutputBundle | None = None

        print("\n======================================")
        print("BEGIN MODEL PIPELINE")
        print("======================================\n")

        for model_name in self.ROUTE_CHAIN:

            runner = self.runners[model_name]

            print("-------------------------------------")
            print(f"MODEL: {model_name}")
            print("-------------------------------------")

            result: AIOutputBundle = runner.produce_output(context_payload)

            last_result = result

            raw_output = result.payload.get("raw_model_output", "")
            confidence = result.confidence_band or 0.0

            print(raw_output)
            print(f"\n[Router] {model_name} confidence = {confidence:.3f}")

            # ---------------------------------------------
            # stop escalation if confident
            # ---------------------------------------------

            if confidence >= self.CONFIDENCE_THRESHOLD:

                print("[Router] Confidence threshold met.")
                print("[Router] Accepting result.\n")

                return result

            # ---------------------------------------------
            # prepare critique payload
            # ---------------------------------------------

            print("[Router] Confidence too low.")
            print("[Router] Passing result to next model for critique.\n")

            context_payload = {
                "question": input_payload.get("question"),
                "previous_model_output": raw_output
            }

        # -------------------------------------------------
        # fallback
        # -------------------------------------------------

        if last_result is None:
            raise RuntimeError("Model routing failed to produce output")

        print("[Router] Escalation chain exhausted.")
        print("[Router] Returning strongest available result.\n")

        return last_result