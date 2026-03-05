class CalibrationPolicy:
    '''
    Pure adaptive calibration policy.

    Computes recommended adjustment magnitudes
    based on stability, drift, and escalation.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, stability=None, drift=None, escalation=None):
        stability = stability or {}
        drift = drift or {}
        escalation = escalation or {}

        stability_index = stability.get("stability_index", 0)
        drift_score = drift.get("drift_score", 0)
        pressure = escalation.get("pressure", 0)

        adjustment = 0

        if drift_score > 0:
            adjustment += drift_score

        if pressure > 0:
            adjustment += pressure

        if stability_index < 0:
            adjustment += abs(stability_index)

        return {
            "recommended_adjustment": adjustment,
            "stability_index": stability_index,
            "drift_score": drift_score,
            "pressure": pressure,
        }
