class IntegrityPolicy:
    '''
    Pure integrity pressure policy.

    Combines:
    - Stability signal
    - Drift signal

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, *, stability, drift):
        stability_index = stability.get("stability_index", 0)
        confidence = stability.get("confidence", 0.0)

        drift_score = drift.get("drift_score", 0)
        trend = drift.get("trend", 0.0)

        # Integrity pressure rises when:
        # - Stability is low
        # - Drift is high
        # - Negative trend indicates destabilization

        pressure = (drift_score - stability_index)

        return {
            "integrity_pressure": pressure,
            "trend": trend,
            "confidence": confidence,
        }
