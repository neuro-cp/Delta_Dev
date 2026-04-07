class RecallBridge:
    """
    Converts semantic recall suggestions into a usable decision.

    Properties:
    - Pure interpreter (no mutation, no memory writes)
    - Uses pressure as gating signal
    - Supports answer recovery when available
    - Safe fallback if only semantic_id exists
    """

    def __init__(
        self,
        pressure_threshold: float = 0.5,
        min_confidence: float = 0.5,
    ):
        self.pressure_threshold = pressure_threshold
        self.min_confidence = min_confidence

    def interpret(self, suggestions, inquiry):
        """
        Convert recall suggestions into execution-ready output.

        Expected suggestion fields (best-effort):
        - semantic_id (required)
        - pressure (optional)
        - answer (optional, future)
        - confidence (optional, future)
        """

        if not suggestions:
            return None

        top = suggestions[0]

        pressure = float(getattr(top, "pressure", 0.0))

        # ---------------------------------
        # 1) Gate on pressure
        # ---------------------------------
        if pressure < self.pressure_threshold:
            return None

        # ---------------------------------
        # 2) Try to extract real answer (future-ready)
        # ---------------------------------
        answer = getattr(top, "answer", None)

        if answer:
            confidence = float(getattr(top, "confidence", pressure))
            confidence = max(self.min_confidence, min(1.0, confidence))

            return {
                "answer": answer,
                "confidence": confidence,
                "source": "recall",
                "semantic_id": getattr(top, "semantic_id", None),
            }

        # ---------------------------------
        # 3) Fallback (current system behavior)
        # ---------------------------------
        return {
            "answer": f"[RECALL] semantic_id={getattr(top, 'semantic_id', 'unknown')}",
            "confidence": min(1.0, max(self.min_confidence, pressure)),
            "source": "recall",
            "semantic_id": getattr(top, "semantic_id", None),
        }