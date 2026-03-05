# engine/salience/sources/sources.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol, Iterable, List


# ============================================================
# Salience Update
# ============================================================

@dataclass(frozen=True)
class SalienceUpdate:
    """
    Proposed salience change emitted by a source.

    NOTE:
    - This is a proposal, not an action.
    - SaliencePolicy decides whether it is allowed.
    """

    channel_id: str
    delta: float
    source: str


# ============================================================
# Salience Source Interface
# ============================================================

class SalienceSource(Protocol):
    """
    Abstract salience source.

    A source:
    - Observes system state (passed in explicitly)
    - Emits zero or more SalienceUpdate proposals
    - Has no side effects
    - Has no authority

    Sources DO NOT:
    - Apply salience directly
    - Know about decision latch
    - Know about dopamine
    - Know about episode boundaries
    """

    name: str

    def compute(self, observation: Dict[str, float]) -> Iterable[SalienceUpdate]:
        """
        Compute salience updates from an observation snapshot.

        observation:
            A flat, read-only dict of signals relevant to this source.
            (e.g., dominance delta, novelty score, region mass deviation)

        Returns:
            Iterable of SalienceUpdate proposals (possibly empty)
        """
        ...


# ============================================================
# Utilities
# ============================================================

def single_update(
    channel_id: str,
    delta: float,
    source: str,
) -> Iterable[SalienceUpdate]:
    """
    Convenience helper for simple sources that emit one update.
    """
    return (SalienceUpdate(channel_id, delta, source),)


# ============================================================
# Source Registry (Declarative)
# ============================================================

def default_salience_sources() -> List[SalienceSource]:
    """
    Construct the default set of salience sources.

    This function is intentionally explicit and declarative.
    Order does NOT imply priority.
    """
    from engine.salience.sources.competition_source import CompetitionSource
    from engine.salience.sources.persistence_source import PersistenceSource
    from engine.salience.sources.surprise_source import SurpriseSource
    from engine.salience.sources.sensory_persistence_source import (
        SensoryPersistenceSource,
    )

    return [
        CompetitionSource(),
        PersistenceSource(),
        SurpriseSource(),
        SensoryPersistenceSource(
            sensory_regions=[
                "visual_input",
                "auditory_input",
                "somato_input",
                "gustatory_input",
            ],
        ),
    ]
