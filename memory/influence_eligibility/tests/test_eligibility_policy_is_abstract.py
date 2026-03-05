from __future__ import annotations

import pytest

from memory.influence_eligibility.eligibility_policy import (
    InfluenceEligibilityPolicy,
)


def test_policy_is_abstract_and_not_instantiable() -> None:
    with pytest.raises(TypeError):
        InfluenceEligibilityPolicy()  # type: ignore[abstract]
