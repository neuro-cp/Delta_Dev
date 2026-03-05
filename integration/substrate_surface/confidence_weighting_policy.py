class ConfidenceWeightingPolicy:
    """
    Confidence attenuates magnitude.

    Never amplifies.
    """

    @staticmethod
    def apply(magnitude: float, confidence: float | None) -> float:
        if confidence is None:
            return magnitude

        return magnitude * max(0.0, min(1.0, confidence))
