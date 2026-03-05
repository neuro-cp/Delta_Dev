class GovernanceRecordPolicy:
    '''
    Pure governance record policy.

    Binds structural outputs into a single immutable artifact.

    Contract:
    - Pure
    - Deterministic
    - No mutation
    - No runtime access
    '''

    def compute(
        self,
        *,
        fragility=None,
        envelope=None,
        application=None,
    ):
        fragility = fragility or {}
        envelope = envelope or {}
        application = application or {}

        return {
            "fragility_index": fragility.get("fragility_index", 0),
            "allowed_adjustment": envelope.get("allowed_adjustment", 0),
            "max_adjustment": envelope.get("max_adjustment", 0),
            "proposed_adjustment": application.get("proposed_adjustment", 0),
            "applied_adjustment": application.get("applied_adjustment", 0),
            "was_clamped": application.get("was_clamped", False),
        }
