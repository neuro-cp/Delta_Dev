class ContainmentEnvelopePolicy:
    '''
    Pure containment envelope policy.

    Computes allowable calibration magnitude
    based on fragility index.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, fragility=None, max_adjustment=10):
        fragility = fragility or {}

        fragility_index = fragility.get("fragility_index", 0)

        # Convert fragility into normalized ratio
        # Bound ratio to [0, 1]
        if max_adjustment <= 0:
            fragility_ratio = 0.0
        else:
            fragility_ratio = min(1.0, fragility_index / max_adjustment)

        # Reduce allowed adjustment proportionally
        allowed = int(max_adjustment * (1.0 - fragility_ratio))

        return {
            "allowed_adjustment": allowed,
            "fragility_index": fragility_index,
            "fragility_ratio": fragility_ratio,
            "max_adjustment": max_adjustment,
        }