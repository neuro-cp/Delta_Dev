from typing import Dict, List


class RoleMatrix:
    """
    Pure mapping of AIRole to allowed influence targets.

    No runtime access.
    No execution coupling.
    """

    _ROLE_TARGETS: Dict[str, List[str]] = {
        "strategic_defense_advisor": ["VALUE_BIAS", "PFC_CONTEXT_GAIN"],
        "simulation_evaluator": ["VALUE_BIAS"],
        "civilian_policy_model": ["PFC_CONTEXT_GAIN"],
    }

    @classmethod
    def allowed_targets(cls, role: str) -> List[str]:
        return cls._ROLE_TARGETS.get(role, [])
