from __future__ import annotations

import time

from memory.context.runtime_context import RuntimeContext
from memory.context.context_policy import ContextPolicy


DT = 0.1


def main() -> None:
    print("=== CONTEXT MEMORY CHARACTERIZATION TEST ===")

    ctx = RuntimeContext(decay_tau=10.0)
    assembly = "pfc:L2:0"

    # Sweep different gain magnitudes
    gains = [0.1, 0.2, 0.3, 0.5, 0.8]

    for gain in gains:
        print(f"\n--- Testing sustained gain = {gain:.2f} ---")

        # Reset salience
        ctx.add_gain(assembly, -10.0)
        for _ in range(5):
            ctx.step(DT)
            time.sleep(DT)

        # Apply sustained gain
        ctx.add_gain(assembly, gain)

        start = time.time()
        while time.time() - start < ContextPolicy.TRACE_MIN_DURATION + 0.2:
            ctx.step(DT)
            time.sleep(DT)

        stats = ctx.stats()
        mem = stats["memory"]

        print(
            f"gain={gain:.2f} | "
            f"trace_count={mem['count']} | "
            f"max_strength={mem['max_strength']:.3f}"
        )

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
