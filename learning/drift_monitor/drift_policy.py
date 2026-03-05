class DriftPolicy:
    '''
    Pure drift monitoring policy.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, stability_history):
        total = len(stability_history)

        if total < 2:
            return {
                "drift_score": 0,
                "trend": 0.0,
            }

        deltas = []
        for i in range(1, total):
            prev = stability_history[i - 1]["stability_index"]
            curr = stability_history[i]["stability_index"]
            deltas.append(curr - prev)

        drift_score = sum(abs(d) for d in deltas)
        trend = sum(deltas) / len(deltas)

        return {
            "drift_score": drift_score,
            "trend": trend,
        }
