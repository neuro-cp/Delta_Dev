# integration/translation/text_to_signal_adapter.py

from typing import Dict, Any, List

from integration.transformation.structured_signal import StructuredCognitiveSignal
from integration.ai_surface.ai_role_declaration import AIRole
from integration.ai_surface.ai_mode_declaration import AIMode


class TextToSignalAdapter:
    """
    Deterministic translator layer.

    Purpose:
    - Convert normalized external payloads into StructuredCognitiveSignal
    - Validate role and mode against declared enums
    - Enforce structural integrity
    - Perform zero policy interpretation
    - Perform zero runtime access

    Contract:
    - Pure
    - Deterministic
    - No substrate coupling
    - No execution authority
    """

    def translate(self, raw_payload: Dict[str, Any]) -> StructuredCognitiveSignal:
        """
        Translate structured external input into StructuredCognitiveSignal.

        Expected raw_payload structure:
        {
            "semantic_tokens": List[str],
            "quantitative_fields": Dict[str, float],
            "role": str,
            "mode": str,
            "confidence": float (optional)
        }
        """

        semantic_tokens = self._validate_tokens(raw_payload.get("semantic_tokens"))
        quantitative_fields = self._validate_quant_fields(
            raw_payload.get("quantitative_fields", {})
        )
        role = self._validate_role(raw_payload.get("role"))
        mode = self._validate_mode(raw_payload.get("mode"))
        confidence = self._validate_confidence(raw_payload.get("confidence"))

        return StructuredCognitiveSignal(
            semantic_tokens=semantic_tokens,
            quantitative_fields=quantitative_fields,
            role=role,
            mode=mode,
            confidence=confidence,
        )

    # -------------------------
    # Validation helpers
    # -------------------------

    def _validate_tokens(self, tokens: Any) -> List[str]:
        if tokens is None:
            raise ValueError("semantic_tokens must be provided")

        if not isinstance(tokens, list):
            raise TypeError("semantic_tokens must be a list of strings")

        for t in tokens:
            if not isinstance(t, str):
                raise TypeError("semantic_tokens must contain only strings")

        return tokens

    def _validate_quant_fields(self, fields: Any) -> Dict[str, float]:
        if not isinstance(fields, dict):
            raise TypeError("quantitative_fields must be a dict[str, float]")

        for k, v in fields.items():
            if not isinstance(k, str):
                raise TypeError("quantitative_fields keys must be strings")
            if not isinstance(v, (int, float)):
                raise TypeError("quantitative_fields values must be numeric")

        return fields

    def _validate_role(self, role: Any) -> str:
        if role is None:
            raise ValueError("role must be provided")

        try:
            AIRole(role)
        except Exception:
            raise ValueError(f"Invalid role: {role}")

        return role

    def _validate_mode(self, mode: Any) -> str:
        if mode is None:
            raise ValueError("mode must be provided")

        try:
            AIMode(mode)
        except Exception:
            raise ValueError(f"Invalid mode: {mode}")

        return mode

    def _validate_confidence(self, confidence: Any):
        if confidence is None:
            return None

        if not isinstance(confidence, (int, float)):
            raise TypeError("confidence must be numeric")

        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0 and 1")

        return float(confidence)