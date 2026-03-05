class StabilityPolicy:
    '''
    Pure stability modeling policy.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, evaluation_history):
        total_cycles = len(evaluation_history)
        if total_cycles == 0:
            return {
                "stability_index": 0,
                "confidence": 0.0,
            }

        aggregate = sum(e["stability_index"] for e in evaluation_history)
        confidence = aggregate / max(total_cycles, 1)

        return {
            "stability_index": aggregate,
            "confidence": confidence,
        }
