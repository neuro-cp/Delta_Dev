from __future__ import annotations

import time

from memory.context.runtime_context import RuntimeContext
from memory.context.context_policy import ContextPolicy


DT = 0.1


def dump(ctx: RuntimeContext, label: str) -> None:
    print(f"\n--- {label} ---")
    stats = ctx.stats()
    print(stats)


def main() -> None:
    print("=== CONTEXT OBSERVATION TEST (POLICY → MEMORY) ===")

    ctx = RuntimeContext(decay_tau=10.0)

    a1 = "pfc:L2:0"

    # ---------------------------------------------------------
    # Case 1: Brief spike (should NOT create a trace)
    # ---------------------------------------------------------
    print("\n[1] Brief spike (no memory expected)")
    ctx.add_gain(a1, ContextPolicy.TRACE_GAIN_THRESHOLD + 0.1)

    # Short duration only
    for _ in range(3):
        ctx.step(DT)
        time.sleep(DT)

    dump(ctx, "after brief spike")

    # ---------------------------------------------------------
    # Case 2: Sustained salience (should create ONE trace)
    # ---------------------------------------------------------
    print("\n[2] Sustained salience (one memory expected)")
    ctx.add_gain(a1, ContextPolicy.TRACE_GAIN_THRESHOLD + 0.2)

    start = time.time()
    while time.time() - start < ContextPolicy.TRACE_MIN_DURATION + 0.2:
        ctx.step(DT)
        time.sleep(DT)

    dump(ctx, "after sustained salience")

    # ---------------------------------------------------------
    # Case 3: Continued persistence (should NOT create new trace)
    # ---------------------------------------------------------
    print("\n[3] Continued persistence (no duplicate memory)")
    for _ in range(10):
        ctx.step(DT)
        time.sleep(DT)

    dump(ctx, "after continued persistence")

    # ---------------------------------------------------------
    # Case 4: Drop below threshold, then re-sustain (new trace allowed)
    # ---------------------------------------------------------
    print("\n[4] Drop below threshold, then re-sustain (second memory expected)")
    ctx.add_gain(a1, -10.0)  # force drop
    for _ in range(5):
        ctx.step(DT)
        time.sleep(DT)

    ctx.add_gain(a1, ContextPolicy.TRACE_GAIN_THRESHOLD + 0.3)
    start = time.time()
    while time.time() - start < ContextPolicy.TRACE_MIN_DURATION + 0.2:
        ctx.step(DT)
        time.sleep(DT)

    dump(ctx, "after second sustained episode")

    print("\n=== TEST COMPLETE ===")


if __name__ == "__main__":
    main()
