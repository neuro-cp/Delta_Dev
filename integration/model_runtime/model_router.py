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
import os

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.model_runtime.gguf_model_runner import GGUFModelRunner
from integration.model_runtime.model_registry import list_available_models


class ModelRouter:
    """
    Deterministic deliberative multi-model router.
    """

    DESKTOP_ROUTE_CHAIN: List[str] = [
        "phi3",
        "phi4",
        "qwen",
        "llama",
    ]

    LAPTOP_ROUTE_CHAIN: List[str] = [
        "phi3",
        "qwen",
    ]

    DESKTOP_CONFIDENCE_THRESHOLD: float = 0.78
    LAPTOP_CONFIDENCE_THRESHOLD: float = 0.78

    def __init__(self) -> None:
        self.profile = os.getenv("DELTA_MACHINE_PROFILE", "desktop").strip().lower()

        if self.profile == "laptop":
            route_chain = list(self.LAPTOP_ROUTE_CHAIN)
            self.confidence_threshold = self.LAPTOP_CONFIDENCE_THRESHOLD
        else:
            route_chain = list(self.DESKTOP_ROUTE_CHAIN)
            self.confidence_threshold = self.DESKTOP_CONFIDENCE_THRESHOLD

        max_models = os.getenv("DELTA_MAX_MODELS", "").strip()
        if max_models:
            try:
                n = max(1, int(max_models))
                route_chain = route_chain[:n]
            except Exception:
                pass

        available = set(list_available_models())
        route_chain = [name for name in route_chain if name in available]
        if not route_chain:
            raise RuntimeError("No configured local models are available")

        self.route_chain = route_chain
        self.runners: Dict[str, GGUFModelRunner] = {
            model_name: GGUFModelRunner(model_name)
            for model_name in self.route_chain
        }

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
        print(f"[Router] Machine profile = {self.profile}")
        print(f"[Router] Route chain = {self.route_chain}")
        print(f"[Router] Confidence threshold = {self.confidence_threshold}\n")

        for model_name in self.route_chain:
            runner = self.runners[model_name]

            print("-------------------------------------")
            print(f"MODEL: {model_name}")
            print("-------------------------------------")

            result: AIOutputBundle = runner.produce_output(context_payload)
            last_result = result

            raw_output = result.payload.get("raw_model_output", "")
            confidence = result.confidence_band or 0.0

            #print(raw_output)
            print(f"\n[Router] {model_name} confidence = {confidence:.3f}")

            if confidence >= self.confidence_threshold:
                print("[Router] Confidence threshold met.")
                print("[Router] Accepting result.\n")
                return result

            print("[Router] Confidence too low.")

            if model_name != self.route_chain[-1]:
                print("[Router] Passing result to next model for critique.\n")
                context_payload = {
                    "question": input_payload.get("question"),
                    "previous_model_output": raw_output,
                }
            else:
                print("[Router] No more models available in this profile.\n")

        if last_result is None:
            raise RuntimeError("Model routing failed to produce output")

        print("[Router] Escalation chain exhausted.")
        print("[Router] Returning strongest available result.\n")

        return last_result
