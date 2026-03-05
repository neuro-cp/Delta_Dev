from __future__ import annotations

import math
from collections import defaultdict

from engine.salience.salience_sparsity_gate import SalienceSparsityGate


def main() -> None:
    print("=== TEST 5A: Sparsity gate induces lawful asymmetry ===")

    # --------------------------------------------------
    # Synthetic symmetric assemblies
    # --------------------------------------------------
    assemblies = [
        f"striatum:D1:{i}" for i in range(20)
    ] + [
        f"striatum:D2:{i}" for i in range(20)
    ]

    # All assemblies receive identical base input
    BASE_INPUT = 1.0

    # --------------------------------------------------
    # Initialize sparsity gate
    # --------------------------------------------------
    gate = SalienceSparsityGate(
        keep_ratio=0.3,
        seed=42,
    )
    gate.initialize(assemblies)

    stats = gate.stats()
    assert stats["initialized"] is True
    assert 0 < stats["eligible"] < stats["total"]

    # --------------------------------------------------
    # Apply symmetric input + sparsity
    # --------------------------------------------------
    channel_mass = defaultdict(float)

    for aid in assemblies:
        channel = aid.split(":")[1]  # D1 or D2

        if gate.allows(aid):
            channel_mass[channel] += BASE_INPUT

    d1 = channel_mass["D1"]
    d2 = channel_mass["D2"]

    print(f"D1 mass = {d1:.3f}")
    print(f"D2 mass = {d2:.3f}")

    # --------------------------------------------------
    # Assertions
    # --------------------------------------------------
    assert d1 != d2, (
        "Sparsity gate failed to induce asymmetry under symmetric drive"
    )

    delta = abs(d1 - d2)
    assert delta > 0.0, "Dominance delta must be non-zero"

    print("[PASS] Structural sparsity produces dominance variance")
    print(f"Dominance delta = {delta:.3f}")


if __name__ == "__main__":
    main()
