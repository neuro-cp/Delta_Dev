from __future__ import annotations

from engine.runtime import BrainRuntime
from engine.vta_value.value_signal import ValueSignal

DT = 0.01
STEPS = 200


def main() -> None:
    print("=== TEST: Value cannot trigger decisions ===")

    # Minimal brain with NO competitive structure
    brain = {
        "regions": {},
    }

    rt = BrainRuntime(brain, dt=DT)

    # --- Critical test constraints ---
    rt.enable_competition = False
    rt.enable_decision_bias = False
    rt.enable_decision_fx = False
    rt.enable_pfc_adapter = False   # ✅ REQUIRED
    rt.enable_context = False
    rt.enable_salience = False

    # Value is allowed to run
    rt.enable_vta_value = True

    # Inject tonic value
    rt.value_signal.set(1.0)

    for _ in range(STEPS):
        rt.step()

    # No decision must ever appear
    assert rt.get_decision_state() is None, (
        "Value alone should never produce a decision"
    )

    print("[PASS] Value does not trigger decisions")


if __name__ == "__main__":
    main()
