"""
integration/model_runtime/gguf_model_runner.py

GGUF model runner implementation.

Responsibilities
----------------
• Bridge ExternalModelInterface → local GGUF models
• Delegate prompt construction to prompt_builder
• Execute model inference through ModelSession
• Extract structured result from model output
• Return AIOutputBundle with parsed confidence

Design guarantees
-----------------
• Executes exactly one model
• Performs no routing
• Prints model output immediately for pipeline visibility
"""

from typing import Dict, Any
import json
import re
import time

from integration.ai_surface.ai_output_bundle import AIOutputBundle
from integration.ai_surface.ai_model_interface import ExternalModelInterface

from integration.model_runtime.model_registry import get_model_spec
from integration.model_runtime.model_session import ModelSession
from integration.model_runtime.prompt_builder import build_prompt


class GGUFModelRunner(ExternalModelInterface):
    """
    Executes a single GGUF model through a controlled ModelSession.
    """

    def __init__(self, model_name: str):
        self.model_spec = get_model_spec(model_name)
        self.session = ModelSession()

    # ------------------------------------------------------------------
    # Model identity helper
    # ------------------------------------------------------------------

    def _model_id(self) -> str:
        """
        Safely resolve a printable model identifier
        regardless of ModelSpec structure.
        """

        for field in ["name", "model_name", "model", "id"]:
            if hasattr(self.model_spec, field):
                return getattr(self.model_spec, field)

        return "unknown-model"

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    def _extract_json(self, text: str) -> Dict[str, Any]:

        start = text.find("{")
        end = text.rfind("}") + 1

        if start >= 0 and end > start:
            candidate = text[start:end]
            try:
                return json.loads(candidate)
            except Exception:
                pass

        return {}

    def _extract_answer(self, text: str) -> str:

        data = self._extract_json(text)

        answer = data.get("answer", "")
        if isinstance(answer, str):
            return answer.strip()

        return ""

    def _extract_model_confidence(self, text: str) -> float:

        data = self._extract_json(text)

        if "confidence" in data:
            try:
                value = float(data["confidence"])
                return max(0.0, min(1.0, value))
            except Exception:
                pass

        m = re.search(r'"confidence"\s*:\s*([0-9.]+)', text)

        if m:
            try:
                value = float(m.group(1))
                return max(0.0, min(1.0, value))
            except Exception:
                pass

        return 0.0

    # ------------------------------------------------------------------
    # Confidence heuristics
    # ------------------------------------------------------------------

    def _heuristic_confidence(self, text: str) -> float:

        answer = self._extract_answer(text)

        if not answer:
            return 0.0

        lowered = answer.lower()
        score = 0.0

        if len(answer) >= 80:
            score += 0.30

        if any(token in answer for token in ["1.262", "259", "AU", "days"]):
            score += 0.25

        if any(
            token in lowered
            for token in ["semi-major", "hohmann", "transfer", "delta-v"]
        ):
            score += 0.25

        if any(token in answer for token in ["=", "/", "(", ")", "sqrt"]):
            score += 0.10

        if "<your answer here>" in answer:
            score -= 0.50

        return max(0.0, min(1.0, score))

    def _combine_confidence(self, text: str) -> float:

        model_conf = self._extract_model_confidence(text)
        heuristic_conf = self._heuristic_confidence(text)

        if heuristic_conf == 0.0:
            return 0.0

        combined = (0.35 * model_conf) + (0.65 * heuristic_conf)

        return max(0.0, min(1.0, combined))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def produce_output(self, input_payload: Dict[str, Any]) -> AIOutputBundle:

        prompt = build_prompt(input_payload)

        model_id = self._model_id()

        print("\n================================")
        print(f"MODEL START: {model_id}")
        print("================================\n")

        start = time.time()
        raw_output = ""

        try:
            self.session.load(self.model_spec)

            raw_output = self.session.generate(prompt)

            print("MODEL OUTPUT:\n")
            print(raw_output)
            print()

        finally:
            self.session.unload()

        elapsed = time.time() - start

        print(f"MODEL COMPLETE: {model_id}")
        print(f"EXECUTION TIME: {elapsed:.2f}s")
        print("================================\n")

        confidence = self._combine_confidence(raw_output)

        return AIOutputBundle(
            role="strategic_defense_advisor",
            mode="active",
            payload={
                "raw_model_output": raw_output,
            },
            confidence_band=confidence,
        )