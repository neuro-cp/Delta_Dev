from __future__ import annotations

import time
from typing import Dict, Any

from engine.decision_fx.decision_effects import DecisionEffects
from engine.decision_fx.decision_policy import DecisionPolicy
from engine.decision_fx.decision_router import DecisionRouter
from engine.decision_fx.decision_trace import DecisionTrace
from engine.decision_fx.runtime_hook import DecisionRuntimeHook


# ============================================================
# CONFIG
# ============================================================

DT = 0.1

WINNER = "D1"
CHANNELS = ["D1", "D2"]

# Synthetic decision signals
DELTA_DOMINANCE = 0.24
RELIEF = 0.71

# Bias strength per channel (synthetic)
BIAS_STRENGTH = 0.8


# ============================================================
# MAIN TEST
# ============================================================

def main() -> None:
    print("=== DECISION FX CLOSED-ENVIRONMENT TEST ===\n")

    # --------------------------------------------------------
    # Instantiate components (NO constructor args)
    # --------------------------------------------------------
    effects = DecisionEffects()
    trace = DecisionTrace()
    hook = DecisionRuntimeHook()

    print("[OK] Components instantiated")

    # --------------------------------------------------------
    # Build synthetic decision state
    # --------------------------------------------------------
    decision_state = {
        "time": 0.0,
        "step": 0,
        "winner": WINNER,
        "delta_dominance": DELTA_DOMINANCE,
        "relief": RELIEF,
    }

    bias_map = {ch: BIAS_STRENGTH for ch in CHANNELS}

    print("\n[TEST] Synthetic decision state")
    print("decision_state:", decision_state)
    print("bias_map:", bias_map)

    # --------------------------------------------------------
    # Policy computation
    # --------------------------------------------------------
    policy_snapshot: Dict[str, Any] = DecisionPolicy.compute(
        decision_state=decision_state,
        bias_map=bias_map,
    )

    print("\n[OK] Policy computed")
    print("policy:", policy_snapshot)

    # --------------------------------------------------------
    # Route policy → effects (INTENT ONLY)
    # --------------------------------------------------------
    routed_effects: Dict[str, Any] = DecisionRouter.route(policy_snapshot)

    print("\n[OK] Policy routed")
    print("routed_effects:", routed_effects)

    # --------------------------------------------------------
    # Apply effects (bounded, reversible)
    # --------------------------------------------------------
    applied_effects = effects.apply(
        thalamic_gain=routed_effects.get("thalamic_gain", 1.0),
        region_gain=(
            {routed_effects["cortical_focus"]: 1.2}
            if routed_effects.get("cortical_focus")
            else {}
        ),
        suppress_channels=routed_effects.get("suppress_channels", {}),
        lock_action=routed_effects.get("lock_action", False),
    )

    print("\n[OK] Effects applied")
    print("applied_effects:", applied_effects)

    # --------------------------------------------------------
    # Feed effects into runtime hook
    # --------------------------------------------------------
    hook.ingest(applied_effects)

    print("\n[OK] Runtime hook ingested effects")
    print("thalamic_gain:", hook.thalamic_gain())
    print("lock_action:", hook.lock_action())

    # --------------------------------------------------------
    # Record trace event (as runtime would)
    # --------------------------------------------------------
    trace.record(
        step=decision_state["step"],
        time=decision_state["time"],
        winner=WINNER,
        dominance={ch: bias_map[ch] for ch in CHANNELS},
        delta=DELTA_DOMINANCE,
        relief=RELIEF,
        bias=bias_map,
        effects=applied_effects,
        runtime_hook=hook.snapshot(),
    )

    print("\n[OK] Trace recorded")

    # --------------------------------------------------------
    # Trace inspection
    # --------------------------------------------------------
    print("\n[TRACE DUMP]")
    for row in trace.dump():
        print(row)

    # --------------------------------------------------------
    # Sanity checks
    # --------------------------------------------------------
    print("\n[CHECKS]")

    if hook.thalamic_gain() <= 0.0:
        print("[FAIL] Thalamic gain invalid")
    else:
        print("[OK] Thalamic gain active")

    if policy_snapshot["commit"] and not hook.lock_action():
        print("[FAIL] Commit policy did not lock action")
    else:
        print("[OK] Action lock consistent with policy")

    if not trace.dump():
        print("[FAIL] No trace entries recorded")
    else:
        print("[OK] Trace entries present")

    print("\n=== DECISION FX TEST COMPLETE ===")


if __name__ == "__main__":
    main()
