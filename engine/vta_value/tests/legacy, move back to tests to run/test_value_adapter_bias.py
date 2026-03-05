from __future__ import annotations

import math

from engine.decision_bias import DecisionBias
from engine.vta_value.value_signal import ValueSignal
from engine.vta_value.value_adapter import ValueAdapter


DT = 0.1


def main():
    print("=== TEST: ValueAdapter → DecisionBias (correct invariants) ===")

    bias = DecisionBias(decay_tau=4.0, max_bias=0.30)
    value = ValueSignal(decay_tau=6.0)
    adapter = ValueAdapter(decision_bias_gain=0.5)

    # --------------------------------------------------
    # Seed a real decision bias
    # --------------------------------------------------
    bias.apply_decision(
        winner="D1",
        channels=["D1", "D2"],
        strength=1.0,
        step=0,
    )

    base = bias.get("D1")
    assert base > 0.0, "Base bias not initialized"

    # --------------------------------------------------
    # Apply value modulation
    # --------------------------------------------------
    value.set(1.0)

    bias.apply_external(
        lambda m: adapter.apply_to_decision_bias(
            value=value.get(),
            bias_map=m,
        )
    )

    bias.step(DT)

    boosted = bias.get("D1")

    # Invariant 1: value never reduces winner bias
    assert boosted >= base * (1.0 - DT / bias.decay_tau), (
        f"Bias decreased unexpectedly: {boosted:.3f} < {base:.3f}"
    )

    # Invariant 2: value does not exceed hard cap
    assert boosted <= bias.max_bias + 1e-6, "Bias exceeded max_bias"

    # Invariant 3: no new channels introduced
    assert set(bias.dump().keys()) == {"D1", "D2"}, "Unexpected bias channels"

    # --------------------------------------------------
    # Remove value and ensure decay resumes
    # --------------------------------------------------
    value.reset()

    bias.step(DT)
    decayed = bias.get("D1")

    assert decayed < boosted, "Bias failed to decay after value removal"

    print("[PASS] ValueAdapter bias modulation behaves correctly")


if __name__ == "__main__":
    main()
