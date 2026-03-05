class CoherencePolicy:
    '''
    Pure coherence field modeling policy.

    Measures agreement between:
    - stability_index
    - drift_score
    - risk_index
    - envelope_magnitude

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, stability=None, drift=None, risk=None, envelope=None):
        stability = stability or {}
        drift = drift or {}
        risk = risk or {}
        envelope = envelope or {}

        stability_index = stability.get("stability_index", 0)
        drift_score = drift.get("drift_score", 0)
        risk_index = risk.get("risk_index", 0)
        envelope_magnitude = envelope.get("envelope_magnitude", 0)

        values = [
            stability_index,
            drift_score,
            risk_index,
            envelope_magnitude,
        ]

        non_zero = [v for v in values if v != 0]

        if not non_zero:
            coherence_index = 0
        else:
            coherence_index = min(non_zero)

        return {
            "coherence_index": coherence_index,
            "stability_index": stability_index,
            "drift_score": drift_score,
            "risk_index": risk_index,
            "envelope_magnitude": envelope_magnitude,
        }
