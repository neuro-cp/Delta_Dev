from __future__ import annotations

import random
from typing import Dict, Iterable, Optional


class SalienceSparsityGate:
    """
    Deterministic, episode-stable sparsity gate for assemblies.

    ROLE
    ----
    Introduces lawful representational asymmetry *before* competition by
    restricting which assemblies are eligible to receive salience / gain.

    This is a STRUCTURAL gate, not a dynamical one.

    CORE GUARANTEES
    ---------------
    - Binary eligibility (allow / block)
    - Deterministic per episode (seeded)
    - No learning
    - No scaling of activity
    - No decision awareness
    - No runtime mutation
    - Fail-open safety if uninitialized

    This gate creates asymmetry WITHOUT injecting bias.
    """

    def __init__(
        self,
        *,
        keep_ratio: float = 0.25,
        seed: Optional[int] = None,
    ):
        """
        Parameters
        ----------
        keep_ratio : float
            Fraction of assemblies allowed through (0 < keep_ratio ≤ 1).

        seed : Optional[int]
            RNG seed for deterministic selection.
        """
        if not (0.0 < keep_ratio <= 1.0):
            raise ValueError("keep_ratio must be in (0, 1].")

        self.keep_ratio = float(keep_ratio)
        self._seed = seed

        self._eligible: Dict[str, bool] = {}
        self._initialized: bool = False

    # --------------------------------------------------
    # Episode lifecycle
    # --------------------------------------------------

    def initialize(self, assembly_ids: Iterable[str]) -> None:
        """
        Initialize eligibility for a fixed set of assemblies.

        Must be called ONCE per episode BEFORE runtime stepping.
        """
        ids = list(dict.fromkeys(assembly_ids))  # stable dedupe

        # ----------------------------------------------
        # Population-level eligibility filter (optional)
        # ----------------------------------------------
        ids = [
            aid for aid in ids
            if not (
                ":" in aid and
                aid.split(":", 1)[1].startswith("L5_")
            )
            or aid.split(":", 1)[1].startswith("L5A")
        ]

        if not ids:
            self._eligible.clear()
            self._initialized = True
            return


        rng = random.Random(self._seed)
        rng.shuffle(ids)

        keep_n = max(1, int(round(len(ids) * self.keep_ratio)))
        allowed = set(ids[:keep_n])

        self._eligible = {aid: (aid in allowed) for aid in ids}
        self._initialized = True

    def reset(self, *, seed: Optional[int] = None) -> None:
        """
        Reset gate state (e.g. between episodes).

        Optionally reseeds the RNG.
        """
        self._eligible.clear()
        self._initialized = False

        if seed is not None:
            self._seed = seed

    # --------------------------------------------------
    # Query API (hot path)
    # --------------------------------------------------

    def allows(self, assembly_id: str) -> bool:
        """
        Return True if this assembly is eligible.

        Fail-open by design if gate is uninitialized.
        """
        if not self._initialized:
            return True

        return bool(self._eligible.get(assembly_id, False))

    # --------------------------------------------------
    # Diagnostics
    # --------------------------------------------------

    def stats(self) -> Dict[str, float]:
        """
        Return diagnostic statistics for observability.
        """
        if not self._initialized or not self._eligible:
            return {
                "initialized": False,
                "eligible": 0,
                "total": 0,
                "ratio": 0.0,
            }

        total = len(self._eligible)
        eligible = sum(1 for v in self._eligible.values() if v)

        return {
            "initialized": True,
            "eligible": eligible,
            "total": total,
            "ratio": eligible / total if total else 0.0,
        }
