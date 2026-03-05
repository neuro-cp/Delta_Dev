from __future__ import annotations

from typing import Dict, Iterable, Tuple

from engine.cognition.hypothesis import Hypothesis


class HypothesisRegistry:
    """
    Sole owner and lifecycle manager for Hypothesis objects.

    Phase 6.1 guarantees:
    - Registry is inert by default
    - No automatic stepping
    - No runtime or region coupling
    - Read-only exposure to outside systems
    """

    def __init__(self) -> None:
        self._hypotheses: Dict[str, Hypothesis] = {}

    # ------------------------------------------------------------
    # Creation / Removal
    # ------------------------------------------------------------

    def create(self, *, hypothesis_id: str, created_step: int) -> Hypothesis:
        """
        Create and register a new hypothesis.

        Raises if the ID already exists.
        """
        if hypothesis_id in self._hypotheses:
            raise ValueError(f"Hypothesis '{hypothesis_id}' already exists")

        h = Hypothesis(
            hypothesis_id=hypothesis_id,
            created_step=int(created_step),
        )
        self._hypotheses[hypothesis_id] = h
        return h

    def remove(self, hypothesis_id: str) -> None:
        """
        Explicitly remove a hypothesis.
        """
        if hypothesis_id not in self._hypotheses:
            raise KeyError(f"Hypothesis '{hypothesis_id}' not found")
        del self._hypotheses[hypothesis_id]

    # ------------------------------------------------------------
    # Access (read-only by convention)
    # ------------------------------------------------------------

    def get(self, hypothesis_id: str) -> Hypothesis | None:
        """
        Retrieve a hypothesis by ID.
        """
        return self._hypotheses.get(hypothesis_id)

    def all(self) -> Tuple[Hypothesis, ...]:
        """
        Immutable snapshot of all hypotheses.
        """
        return tuple(self._hypotheses.values())

    def __len__(self) -> int:
        return len(self._hypotheses)

    # ------------------------------------------------------------
    # Optional bookkeeping (explicit only)
    # ------------------------------------------------------------

    def tick(self) -> None:
        """
        Explicit age advancement.

        NOTE:
        - This must be called manually.
        - Registry does NOT auto-step.
        """
        for h in self._hypotheses.values():
            if h.active:
                h.age += 1

    # ------------------------------------------------------------
    # Inspection / Audit
    # ------------------------------------------------------------

    def dump_state(self) -> Dict[str, Dict]:
        """
        Stable, audit-safe dump of registry contents.
        """
        return {
            hid: h.to_dict()
            for hid, h in self._hypotheses.items()
        }
