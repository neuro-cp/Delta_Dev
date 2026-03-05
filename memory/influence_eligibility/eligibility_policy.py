from __future__ import annotations

from abc import ABC, abstractmethod

from memory.influence_eligibility.eligibility_record import (
    InfluenceEligibilityRecord,
)


class InfluenceEligibilityPolicy(ABC):
    """
    Abstract eligibility policy.

    Policies evaluate artifacts and emit descriptive
    eligibility records.

    Policies must be:
    - deterministic
    - offline
    - side-effect free
    """

    policy_id: str

    @abstractmethod
    def evaluate(self, artifact: object) -> InfluenceEligibilityRecord:
        raise NotImplementedError
