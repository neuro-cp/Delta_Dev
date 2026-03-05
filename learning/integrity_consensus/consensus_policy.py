class ConsensusPolicy:
    '''
    Pure integrity consensus policy.

    Computes disagreement magnitude between:
    - escalation pressure
    - oversight aggregate
    - calibration adjustment

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, escalation=None, oversight=None, calibration=None):
        escalation = escalation or {}
        oversight = oversight or {}
        calibration = calibration or {}

        pressure = escalation.get("pressure", 0)
        aggregate = oversight.get("aggregate_index", 0)
        adjustment = calibration.get("recommended_adjustment", 0)

        disagreement = abs(pressure - aggregate) + abs(aggregate - adjustment)

        return {
            "pressure": pressure,
            "aggregate_index": aggregate,
            "recommended_adjustment": adjustment,
            "disagreement_score": disagreement,
        }
