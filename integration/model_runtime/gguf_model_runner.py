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
from integration.model_runtime.inference_types import CanonicalInferenceResult


class GGUFModelRunner(ExternalModelInterface):
    """
    Executes a single GGUF model through a controlled ModelSession.
    """

    def __init__(self, model_name: str, *, n_gpu_layers: int | None = None, keep_loaded: bool = False):
        self.model_name = model_name
        self.session = ModelSession(n_gpu_layers=n_gpu_layers)
        self.keep_loaded = keep_loaded

    def load_model(self) -> None:
        model_spec = get_model_spec(self.model_name)
        self.session.load(model_spec)

    def unload(self) -> None:
        self.session.unload()

    # ------------------------------------------------------------------
    # Model identity helper
    # ------------------------------------------------------------------

    def _model_id(self, model_spec) -> str:
        """
        Safely resolve a printable model identifier
        regardless of ModelSpec structure.
        """

        for field in ["name", "model_name", "model", "id"]:
            if hasattr(model_spec, field):
                return getattr(model_spec, field)

        return self.model_name

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

        # If no heuristic signal, trust model
        if heuristic_conf == 0.0:
            return model_conf

        # Model-dominant fusion
        combined = (0.85 * model_conf) + (0.15 * heuristic_conf)

        return max(0.0, min(1.0, round(combined, 4)))

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def produce_output(self, input_payload: Dict[str, Any]) -> AIOutputBundle:
        model_spec = get_model_spec(self.model_name)
        prompt = build_prompt(input_payload)

        model_id = self._model_id(model_spec)

        print("\n================================")
        print(f"MODEL START: {model_id}")
        print("================================\n")

        start = time.time()
        raw_output = ""

        try:
            self.session.load(model_spec)
            raw_output = self.session.generate(prompt)

            #print("MODEL OUTPUT:\n")
            #print(raw_output)
            print()

        finally:
            if not self.keep_loaded:
                self.session.unload()

        elapsed = time.time() - start

        print(f"MODEL COMPLETE: {model_id}")
        print(f"EXECUTION TIME: {elapsed:.2f}s")
        print("================================\n")

        confidence = self._combine_confidence(raw_output)
        answer = self._extract_answer(raw_output) or raw_output.strip()
        canonical = CanonicalInferenceResult(
            provider="local_gguf",
            model_id=model_id,
            answer=answer,
            raw_output=raw_output,
            confidence=confidence,
            latency_seconds=round(elapsed, 4),
            prompt_tokens=len(prompt.split()),
            response_tokens=len(raw_output.split()),
            evidence=[],
            metadata={
                "model_path": model_spec.path,
                "family": model_spec.family,
                "quantization": model_spec.quantization,
                "context_length": model_spec.context_length,
                "capabilities": list(model_spec.capabilities),
            },
        )

        return AIOutputBundle(
            role="strategic_defense_advisor",
            mode="active",
            payload=canonical.to_ai_output_payload(),
            confidence_band=confidence,
        )
