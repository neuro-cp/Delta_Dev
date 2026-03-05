import math

class EntropyPolicy:
    '''
    Pure signal entropy policy.

    Measures dispersion of signal magnitudes.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, signals=None):
        signals = signals or {}

        values = [abs(v) for v in signals.values() if v != 0]

        if not values:
            return {
                "entropy_index": 0.0,
                "signal_count": 0,
            }

        total = sum(values)
        probabilities = [v / total for v in values]

        entropy = 0.0
        for p in probabilities:
            entropy -= p * math.log(p)

        return {
            "entropy_index": entropy,
            "signal_count": len(values),
        }
