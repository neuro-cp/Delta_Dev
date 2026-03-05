from __future__ import annotations

from engine.affective_urgency.urgency_driver import (
    UrgencyDriver,
    UrgencyInputs,
)


def make_inputs(
    *,
    time: float = 0.0,
    time_in_window: float = 0.0,
    phase: str = "pre-decision",
    decision_made: bool = False,
    committed: bool = False,
    suppress_alternatives: bool = False,
    dominance_delta: float = 0.05,
    dominance_stable: bool = True,
    gate_relief: float = 0.6,
) -> UrgencyInputs:
    return UrgencyInputs(
        time=time,
        phase=phase,
        decision_made=decision_made,
        committed=committed,
        suppress_alternatives=suppress_alternatives,
        dominance_delta=dominance_delta,
        dominance_stable=dominance_stable,
        gate_relief=gate_relief,
        time_in_window=time_in_window,
    )


def main() -> None:
    print("=== URGENCY DRIVER RAMP TEST (NO DECISION) ===")

    driver = UrgencyDriver(
        relief_floor=0.45,
        relief_ceiling=0.75,
        delta_floor=0.04,
        ramp_time=2.0,
        max_drive=1.0,
    )

    # --------------------------------------------------
    # CASE 1: Clean ramp with time
    # --------------------------------------------------
    print("\n[CASE 1] Clean ramp with time")

    for t in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]:
        inp = make_inputs(time_in_window=t)
        u = driver.compute(inp)
        print(f"time_in_window={t:4.1f}  urgency={u:.3f}")

    # --------------------------------------------------
    # CASE 2: Below relief floor → zero urgency
    # --------------------------------------------------
    print("\n[CASE 2] Below relief floor")

    inp = make_inputs(
        time_in_window=5.0,
        gate_relief=0.3,
    )
    print("urgency =", driver.compute(inp))

    # --------------------------------------------------
    # CASE 3: Below dominance threshold → zero urgency
    # --------------------------------------------------
    print("\n[CASE 3] Below dominance threshold")

    inp = make_inputs(
        time_in_window=5.0,
        dominance_delta=0.01,
    )
    print("urgency =", driver.compute(inp))

    # --------------------------------------------------
    # CASE 4: Dominance unstable → zero urgency
    # --------------------------------------------------
    print("\n[CASE 4] Dominance unstable")

    inp = make_inputs(
        time_in_window=5.0,
        dominance_stable=False,
    )
    print("urgency =", driver.compute(inp))

    # --------------------------------------------------
    # CASE 5: Suppressing alternatives → zero urgency
    # --------------------------------------------------
    print("\n[CASE 5] Suppress alternatives active")

    inp = make_inputs(
        time_in_window=5.0,
        suppress_alternatives=True,
    )
    print("urgency =", driver.compute(inp))

    # --------------------------------------------------
    # CASE 6: Decision already made → zero urgency
    # --------------------------------------------------
    print("\n[CASE 6] Decision already made")

    inp = make_inputs(
        time_in_window=5.0,
        decision_made=True,
    )
    print("urgency =", driver.compute(inp))

    # --------------------------------------------------
    # CASE 7: Committed → zero urgency
    # --------------------------------------------------
    print("\n[CASE 7] Committed")

    inp = make_inputs(
        time_in_window=5.0,
        committed=True,
    )
    print("urgency =", driver.compute(inp))

    print("\n=== TEST COMPLETE ===")
    print("Expected:")
    print("• urgency ramps smoothly with time")
    print("• urgency shuts off immediately when ineligible")
    print("• urgency never exceeds max_drive")
    print("• no decisions are possible here")


if __name__ == "__main__":
    main()
