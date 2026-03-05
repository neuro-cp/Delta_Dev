class OversightPolicy:
    '''
    Pure meta oversight aggregation policy.

    Aggregates:
    - escalation
    - execution preview
    - drive bias

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, escalation=None, execution=None, drive=None):
        escalation = escalation or {}
        execution = execution or {}
        drive = drive or {}

        total_pressure = escalation.get("pressure", 0)
        execution_surface = sum(execution.values()) if execution else 0
        drive_score = drive.get("score", 0)

        aggregate_index = total_pressure + execution_surface + drive_score

        return {
            "aggregate_index": aggregate_index,
            "pressure": total_pressure,
            "execution_surface": execution_surface,
            "drive_score": drive_score,
        }
