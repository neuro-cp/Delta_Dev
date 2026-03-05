from __future__ import annotations
from typing import List
from engine.population_model import PopulationModel


def differentiate(region_name: str, assemblies: List[PopulationModel], seed: int) -> None:
    """
    Pattern-based structural differentiation.
    Deterministic, bounded, non-semantic.

    STN target:
    - Sparse baseline participation
    - Monotonic recruitment with increasing drive
    - No tonic saturation
    """
    n = len(assemblies)
    if n == 0:
        return

    for i, pop in enumerate(assemblies):
        frac = i / max(1, n - 1)

        if frac < 0.3:
            # Fast / transient cohort
            pop.tau *= 0.6
            if region_name != "stn":
                pop.threshold += 0.05
            pop._structural_gain = 0.9

        elif frac < 0.7:
            # Balanced / recruitable cohort
            if region_name == "stn":
                pop.threshold += 0.02
            pop._structural_gain = 1.0

        else:
            # Persistent / high-threshold cohort
            pop.tau *= 1.5
            pop.homeostatic_gain *= 0.5
            if region_name == "stn":
                pop.threshold += 0.04
            pop._structural_gain = 1.1