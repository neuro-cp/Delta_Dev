from __future__ import annotations

import random
from typing import Dict, List

from regions.assembly_differentiation.seed import get_seed_int


class PVNDifferentiationAdapter:
    """
    Deterministic, reversible assembly-level differentiation
    for the Paraventricular Nucleus (PVN).

    - Deterministically mutes 2 of 5 assemblies
    - Structural only (gain multiplier)
    - No learning, no persistence, no mutation across runs
    """

    TARGET_REGION = "hypothalamus"
    TARGET_POPULATION = "PARAVENTRICULAR_NUCLEUS"
    EXPECTED_ASSEMBLIES = 5

    def __init__(self, attenuation: float = 1.0):
        self.attenuation = float(attenuation)
        self._rng = random.Random(get_seed_int())
        self._muted_ids: List[str] = []

    def apply(self, runtime) -> None:
        region = runtime.region_states.get(self.TARGET_REGION)
        if not region:
            raise RuntimeError("Hypothalamus region not found")

        assemblies = region["populations"].get(self.TARGET_POPULATION)
        if not assemblies:
            raise RuntimeError("PVN population not found")

        if len(assemblies) != self.EXPECTED_ASSEMBLIES:
            raise RuntimeError(
                f"PVN expected {self.EXPECTED_ASSEMBLIES} assemblies, "
                f"found {len(assemblies)}"
            )

        muted = self._rng.sample(assemblies, 2)
        self._muted_ids = [a.assembly_id for a in muted]

        for a in assemblies:
            # structural gain multiplier (default = 1.0)
            base = getattr(a, "_structural_gain", 1.0)
            if a.assembly_id in self._muted_ids:
                a._structural_gain = base * self.attenuation
            else:
                a._structural_gain = base

    def dump_state(self) -> Dict:
        return {
            "muted_assemblies": list(self._muted_ids),
            "attenuation": self.attenuation,
        }
