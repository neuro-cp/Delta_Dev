class MomentumPolicy:
    '''
    Pure structural momentum policy.

    Measures second-order change in stability history.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, stability_history=None):
        stability_history = stability_history or []

        if len(stability_history) < 3:
            return {
                "momentum_index": 0,
                "sample_count": len(stability_history),
            }

        deltas = []
        for i in range(1, len(stability_history)):
            prev = stability_history[i - 1]["stability_index"]
            curr = stability_history[i]["stability_index"]
            deltas.append(curr - prev)

        accelerations = []
        for i in range(1, len(deltas)):
            accelerations.append(deltas[i] - deltas[i - 1])

        momentum_index = sum(accelerations)

        return {
            "momentum_index": momentum_index,
            "sample_count": len(stability_history),
        }
