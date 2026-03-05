from __future__ import annotations

import socket
import time
import csv
import re
from pathlib import Path
from typing import Optional, Tuple

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")

DOM_CSV   = BASE_DIR / "dominance_trace.csv"
DEBUG_CSV = BASE_DIR / "decision_debug_trace.csv"
DEC_CSV   = BASE_DIR / "decision_latch_trace.csv"

DT = 0.01
POLL_TICKS = 25
POLL_SLEEP = DT * POLL_TICKS

BASELINE_STEPS = 20
ASYM_STEPS     = 40
FORCED_STEPS   = 120   # slightly longer to allow near-misses

SMALL_POKE = 1.0

# ============================================================
# PARAMETER SWEEPS (THIS IS THE POINT)
# ============================================================

GATE_THRESHOLDS = [0.10, 0.28, 0.35, 0.47, 0.60]
ASYM_POKES      = [0.5, 1.0, 1.5]

# ============================================================
# EXPERIMENT METADATA
# ============================================================

EXPERIMENT_ID = "latch_gate_characterization_v2"

TEST_BASELINE = 1
TEST_ASYM     = 2
TEST_GATE     = 3

# ============================================================
# TCP
# ============================================================

def send(cmd: str, expect_reply: bool = True) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
            sock.sendall((cmd.strip() + "\n").encode("utf-8"))
            if not expect_reply:
                return ""
            return sock.recv(65535).decode("utf-8", errors="replace").strip()
    except Exception as e:
        print(f"[TCP ERROR] {cmd} :: {e}")
        return ""

def wait_for_server() -> None:
    while True:
        out = send("help")
        if out and "Commands:" in out:
            return
        time.sleep(0.5)

# ============================================================
# PARSING
# ============================================================

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
RE_VAL = re.compile(rf"\b(D1|D2)\b\s*(?:=|:)\s*({_NUM})", re.I)
RE_WIN = re.compile(r"(winner|Winner)\s*(?:=|:)\s*(\w+)", re.I)
RE_T   = re.compile(rf"STRIATUM\s*@\s*t=({_NUM})", re.I)
RE_REL = re.compile(rf"relief\s*=\s*({_NUM})", re.I)

def parse_striatum(out: str) -> Optional[Tuple[str, float, float, float]]:
    if not out:
        return None

    winner = ""
    d1 = d2 = None
    t = 0.0

    for line in out.splitlines():
        if (m := RE_T.search(line)):
            t = float(m.group(1))
        if (m := RE_WIN.search(line)):
            winner = m.group(2)
        if (m := RE_VAL.search(line)):
            if m.group(1).upper() == "D1":
                d1 = float(m.group(2))
            else:
                d2 = float(m.group(2))

    if d1 is None or d2 is None:
        return None

    return winner, d1, d2, t

def parse_gate(out: str) -> Optional[float]:
    if not out:
        return None
    if (m := RE_REL.search(out)):
        return float(m.group(1))
    return None

# ============================================================
# CSV INIT (ONCE)
# ============================================================

def init_csvs() -> None:
    with open(DOM_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "experiment_id","run_id","trial","test_id","step",
            "winner","D1","D2","delta"
        ])

    with open(DEBUG_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "experiment_id","run_id","trial","test_id","step",
            "t_runtime",
            "winner","D1","D2","delta",
            "gate_relief","gate_opened",
            "decision_seen",
            "baseline_poke","asym_poke","gate_threshold",
            "max_delta_so_far","max_relief_so_far"
        ])

    with open(DEC_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "experiment_id","run_id","trial","step","time",
            "winner","delta_dominance","relief"
        ])

# ============================================================
# LOGGING
# ============================================================

def log_step(
    run_id: int,
    trial: int,
    test_id: int,
    step: int,
    t: float,
    winner: str,
    d1: float,
    d2: float,
    delta: float,
    gate: Optional[float],
    gate_opened: bool,
    decision_seen: int,
    max_delta: float,
    max_relief: float,
    asym_poke: float,
    gate_threshold: float,
) -> None:

    with open(DEBUG_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            EXPERIMENT_ID, run_id, trial, test_id, step,
            t,
            winner, d1, d2, delta,
            gate, gate_opened,
            decision_seen,
            SMALL_POKE, asym_poke, gate_threshold,
            max_delta, max_relief
        ])

# ============================================================
# MAIN CHARACTERIZATION SUITE
# ============================================================

def main() -> None:
    print("=== DECISION LATCH CHARACTERIZATION SUITE ===")

    init_csvs()
    wait_for_server()

    run_id = 1
    trial = 0

    for gate_threshold in GATE_THRESHOLDS:
        for asym_poke in ASYM_POKES:

            trial += 1
            print(f"\n--- Trial {trial} | gate={gate_threshold} asym={asym_poke} ---")

            send("reset_latch")

            step = 0
            max_delta = 0.0
            max_relief = 0.0
            decision_seen = 0
            gate_opened = False

            # ---------------------------
            # TEST 1 — Baseline
            # ---------------------------
            for _ in range(BASELINE_STEPS):
                send(f"poke striatum {SMALL_POKE}", expect_reply=False)
                time.sleep(POLL_SLEEP)

                parsed = parse_striatum(send("striatum"))
                if not parsed:
                    continue

                winner, d1, d2, t = parsed
                delta = abs(d1 - d2)

                log_step(
                    run_id, trial, TEST_BASELINE,
                    step, t, winner, d1, d2, delta,
                    None, gate_opened, decision_seen,
                    max_delta, max_relief,
                    asym_poke, gate_threshold
                )
                step += 1

            # ---------------------------
            # TEST 2 — Asymmetry
            # ---------------------------
            for _ in range(ASYM_STEPS):
                send(f"poke striatum:D1_MSN {asym_poke}", expect_reply=False)
                time.sleep(POLL_SLEEP)

                parsed = parse_striatum(send("striatum"))
                if not parsed:
                    continue

                winner, d1, d2, t = parsed
                delta = abs(d1 - d2)
                max_delta = max(max_delta, delta)

                log_step(
                    run_id, trial, TEST_ASYM,
                    step, t, winner, d1, d2, delta,
                    None, gate_opened, decision_seen,
                    max_delta, max_relief,
                    asym_poke, gate_threshold
                )
                step += 1

            # ---------------------------
            # TEST 3 — Gate-driven
            # ---------------------------
            for _ in range(FORCED_STEPS):
                send(f"poke striatum {SMALL_POKE}", expect_reply=False)
                time.sleep(POLL_SLEEP)

                gate = parse_gate(send("gate"))
                parsed = parse_striatum(send("striatum"))
                if not parsed:
                    continue

                winner, d1, d2, t = parsed
                delta = abs(d1 - d2)

                if gate is not None:
                    max_relief = max(max_relief, gate)

                if gate is not None and gate >= gate_threshold and not gate_opened:
                    gate_opened = True
                    send(f"poke striatum:D1_MSN {asym_poke}", expect_reply=False)

                dec = send("decision")
                if dec.startswith("DECISION:") and "none" not in dec.lower():
                    decision_seen = 1
                    with open(DEC_CSV, "a", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerow([
                            EXPERIMENT_ID, run_id, trial, step, t,
                            winner, delta, gate
                        ])
                    break

                log_step(
                    run_id, trial, TEST_GATE,
                    step, t, winner, d1, d2, delta,
                    gate, gate_opened, decision_seen,
                    max_delta, max_relief,
                    asym_poke, gate_threshold
                )
                step += 1

    print("\n=== CHARACTERIZATION COMPLETE ===")

if __name__ == "__main__":
    main()
