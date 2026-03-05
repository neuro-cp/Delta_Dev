from __future__ import annotations

import time
from typing import Dict

# ------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------
from memory.context.runtime_context import RuntimeContext


DT = 0.1          # simulated timestep
DECAY_TAU = 2.0   # fast decay so behavior is visible
STEPS = 20


def dump(ctx: RuntimeContext, label: str) -> None:
    print(f"\n--- {label} ---")
    stats = ctx.stats()
    if not stats:
        print("(empty)")
    else:
        print(stats)


def main() -> None:
    print("=== CONTEXT MEMORY BASIC TEST ===")

    ctx = RuntimeContext(decay_tau=DECAY_TAU)

    # Synthetic assembly IDs
    a1 = "pfc:L2:0"
    a2 = "pfc:L2:1"

    # --------------------------------------------------------
    # Initial injection
    # --------------------------------------------------------
    print("\n[1] Inject initial context")
    ctx.add_gain(a1, 1.0)
    ctx.add_gain(a2, 0.5)
    ctx.add_gain("__global__", 0.25)

    dump(ctx, "after injection")

    # --------------------------------------------------------
    # Passive decay
    # --------------------------------------------------------
    print("\n[2] Passive decay")
    for _ in range(STEPS):
        ctx.step(DT)
        time.sleep(0.01)

    dump(ctx, "after decay")

    # --------------------------------------------------------
    # Reinforcement of one assembly only
    # --------------------------------------------------------
    print("\n[3] Reinforce only a1")
    ctx.add_gain(a1, 0.75)

    for _ in range(STEPS):
        ctx.step(DT)
        time.sleep(0.01)

    dump(ctx, "after reinforcement + decay")

    # --------------------------------------------------------
    # Observational checks
    # --------------------------------------------------------
    g1 = ctx.get_gain(a1)
    g2 = ctx.get_gain(a2)
    gg = ctx.get_gain("__global__")

    print("\n[4] Sanity checks")
    print(f"a1 gain = {g1:.6f}")
    print(f"a2 gain = {g2:.6f}")
    print(f"global gain = {gg:.6f}")

    if g1 <= g2:
        print("⚠️  WARNING: reinforced assembly did not dominate decay")
    else:
        print("✅ Reinforcement dominance confirmed")

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
