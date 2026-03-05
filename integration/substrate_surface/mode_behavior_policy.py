class ModeBehaviorPolicy:
    """
    Deterministic envelope shaping for AIMode.

    No authority granted.
    Only magnitude shaping.
    """

    _MODE_CAP = {
        "active": 1.0,
        "passive": 0.10,
        "integrative_evaluative": 0.5,
    }

    @classmethod
    def apply(cls, mode: str, magnitude: float) -> float:
        cap = cls._MODE_CAP.get(mode, 0.0)
        return min(magnitude, cap)
