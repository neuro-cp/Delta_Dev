class RecallBridge:
    """
    Converts semantic recall suggestions into a usable decision.
    Does NOT modify memory — only interprets.
    """

    def __init__(self, pressure_threshold: float = 1.5):
        self.pressure_threshold = pressure_threshold

    def interpret(self, suggestions, inquiry):
        if not suggestions:
            return None

        top = suggestions[0]
        pressure = getattr(top, "pressure", 0.0)

        if pressure >= self.pressure_threshold:
            return {
                "answer": f"[RECALL] semantic_id={top.semantic_id}",
                "confidence": min(1.0, pressure),
                "source": "recall",
            }

        return None
