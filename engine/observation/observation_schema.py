from __future__ import annotations
from enum import Enum


class ObservationType(str, Enum):
    MASS_SHIFT = "mass_shift"
    FRACTION_ACTIVE = "fraction_active"
    RECRUITMENT_EVENT = "recruitment_event"
    QUIESCENCE = "quiescence"
