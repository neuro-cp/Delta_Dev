class GovernanceGatePolicy:
    '''
    Pure governance gate policy.

    Approves structurally safe governance records.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    CATASTROPHIC_FRAGILITY_RATIO = 0.40 #40

    def compute(self, record=None):
        record = record or {}

        fragility_index = record.get("fragility_index", 0)
        max_adjustment = record.get("max_adjustment", 1)
        was_clamped = record.get("was_clamped", False)

        # Compute fragility ratio safely
        if max_adjustment <= 0:
            fragility_ratio = 0.0
        else:
            fragility_ratio = min(1.0, fragility_index / max_adjustment)

        # Catastrophic fragility threshold
        if fragility_ratio > self.CATASTROPHIC_FRAGILITY_RATIO:
            return {
                "approved": False,
                "reason": "catastrophic_fragility",
                "fragility_ratio": fragility_ratio,
            }

        # Clamping is still a hard failure
        if was_clamped:
            return {
                "approved": False,
                "reason": "adjustment_clamped",
                "fragility_ratio": fragility_ratio,
            }

        return {
            "approved": True,
            "reason": "within_tolerance",
            "fragility_ratio": fragility_ratio,
        }