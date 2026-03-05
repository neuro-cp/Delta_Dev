class EscalationPolicy:
    '''
    Pure governance escalation policy.

    Converts integrity pressure into
    structured escalation levels.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, integrity):
        pressure = integrity.get("integrity_pressure", 0)
        trend = integrity.get("trend", 0.0)

        if pressure <= 0:
            level = "stable"
        elif pressure < 5:
            level = "watch"
        elif pressure < 10:
            level = "elevated"
        else:
            level = "critical"

        return {
            "escalation_level": level,
            "pressure": pressure,
            "trend": trend,
        }
