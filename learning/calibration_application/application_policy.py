class CalibrationApplicationPolicy:
    '''
    Pure calibration application policy.

    Applies containment envelope constraints
    to a proposed adjustment.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, proposed_adjustment=0, allowed_adjustment=0):
        proposed_adjustment = proposed_adjustment or 0
        allowed_adjustment = allowed_adjustment or 0

        if proposed_adjustment <= allowed_adjustment:
            applied = proposed_adjustment
            was_clamped = False
        else:
            applied = allowed_adjustment
            was_clamped = True

        if applied < 0:
            applied = 0

        return {
            "proposed_adjustment": proposed_adjustment,
            "allowed_adjustment": allowed_adjustment,
            "applied_adjustment": applied,
            "was_clamped": was_clamped,
        }
