from __future__ import annotations

import socket
import time
from typing import Dict, Any

from memory.working_state.working_state import WorkingState
from memory.working_state.working_policy import WorkingPolicy
from memory.working_state.working_hook import WorkingRuntimeHook


# ============================================================
# TCP sanity helpers (runtime must be alive, not used for logic)
# ============================================================

HOST = "127.0.0.1"
PORT = 5557


def send(cmd: str) -> str:
    with socket.create_connection((HOST, PORT), timeout=1.0) as s:
        s.sendall((cmd + "\n").encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def wait_for_server(timeout: float = 5.0) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            send("help")
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError("Command server not available")


# ============================================================
# TEST CONFIG
# ============================================================

DT = 0.01

BASELINE_STEPS = 100
HOLD_STEPS = 200
RELEASE_STEPS = 300


# ============================================================
# MAIN TEST
# ============================================================

def main() -> None:
    print("=== WORKING STATE (PFC) BASIC UNIT TEST ===")

    # --------------------------------------------------------
    # Sanity: runtime is alive (integration comes later)
    # --------------------------------------------------------
    wait_for_server()
    send("reset_latch")

    # --------------------------------------------------------
    # Construct working-memory stack (LOCAL, ISOLATED)
    # --------------------------------------------------------
    state = WorkingState(
        decay_tau=50.0,
        sustain_gain=1.0,
    )

    policy = WorkingPolicy(
        min_confidence=0.5,
        allow_override=False,
        release_on_new_decision=True,
    )

    hook = WorkingRuntimeHook(
        state=state,
        policy=policy,
    )

    # --------------------------------------------------------
    # TEST 1 — Baseline: idle means idle
    # --------------------------------------------------------
    print("[TEST 1] Baseline — no decision → no engagement")

    for _ in range(BASELINE_STEPS):
        hook.step(DT)

        assert not hook.is_engaged(), "Working state engaged during baseline"
        assert hook.active_channel() is None, "Active channel present during baseline"

    # --------------------------------------------------------
    # TEST 2 — Synthetic decision engages working state
    # --------------------------------------------------------
    print("[TEST 2] Synthetic decision engages working state")

    decision_state: Dict[str, Any] = {
        "commit": True,
        "winner": "D1",
        "confidence": 0.95,
    }

    hook.ingest(decision_state=decision_state)
    hook.step(DT)

    assert hook.is_engaged(), "Working state did not engage"
    assert hook.active_channel() == "D1", "Incorrect active channel"

    print("  engaged:", hook.is_engaged())
    print("  channel:", hook.active_channel())
    print("  strength:", hook.strength())

    # --------------------------------------------------------
    # TEST 3 — Hold persistence (semantic + monotonic check)
    # --------------------------------------------------------
    print("[TEST 3] Working state persists without input")

    last_strength = hook.strength()

    for _ in range(HOLD_STEPS):
        hook.step(DT)

        assert hook.is_engaged(), "Working state disengaged unexpectedly"
        assert hook.active_channel() == "D1", "Active channel changed unexpectedly"
        assert hook.strength() >= last_strength, "Strength decreased while engaged"

        last_strength = hook.strength()

    # --------------------------------------------------------
    # TEST 4 — No re-entry without override
    # --------------------------------------------------------
    print("[TEST 4] No override when allow_override=False")

    decision_state_2 = {
        "commit": True,
        "winner": "D2",
        "confidence": 1.0,
    }

    hook.ingest(decision_state=decision_state_2)
    hook.step(DT)

    assert hook.active_channel() == "D1", "Override occurred unexpectedly"

    # --------------------------------------------------------
    # TEST 5 — Release semantics (AUTHORITATIVE)
    # --------------------------------------------------------
    print("[TEST 5] Release semantics")

    hook.state.release()

    for _ in range(RELEASE_STEPS):
        hook.step(DT)

    # Engagement is the ONLY semantic contract
    assert not hook.is_engaged(), "Working state still engaged after release"

    # Diagnostics only (do NOT assert)
    print("  post-release channel (diagnostic):", hook.active_channel())
    print("  post-release strength (diagnostic):", hook.strength())

    print("=== WORKING STATE BASIC TEST PASSED ===")


if __name__ == "__main__":
    main()
