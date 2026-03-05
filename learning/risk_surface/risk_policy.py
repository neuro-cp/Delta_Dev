class RiskPolicy:
    '''
    Pure risk surface modeling policy.

    Computes a synthetic risk index based on:
    - envelope magnitude
    - drift trend
    - escalation pressure

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, envelope=None, drift=None, escalation=None):
        envelope = envelope or {}
        drift = drift or {}
        escalation = escalation or {}

        magnitude = envelope.get("envelope_magnitude", 0)
        trend = drift.get("trend", 0.0)
        pressure = escalation.get("pressure", 0)

        risk_index = magnitude + pressure + int(abs(trend))

        return {
            "risk_index": risk_index,
            "envelope_magnitude": magnitude,
            "pressure": pressure,
            "trend": trend,
        }
