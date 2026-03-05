class FragilityPolicy:
    '''
    Pure structural fragility policy.

    Combines coherence, entropy, momentum,
    and escalation pressure into a fragility index.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(self, coherence=None, entropy=None, momentum=None, escalation=None):
        coherence = coherence or {}
        entropy = entropy or {}
        momentum = momentum or {}
        escalation = escalation or {}

        coherence_index = coherence.get("coherence_index", 0)
        entropy_index = entropy.get("entropy_index", 0.0)
        momentum_index = momentum.get("momentum_index", 0)
        pressure = escalation.get("pressure", 0)

        fragility = 0

        if coherence_index == 0 and entropy_index > 0:
            fragility += entropy_index

        if momentum_index > 0:
            fragility += momentum_index

        if pressure > 0:
            fragility += pressure

        return {
            "fragility_index": fragility,
            "coherence_index": coherence_index,
            "entropy_index": entropy_index,
            "momentum_index": momentum_index,
            "pressure": pressure,
        }
