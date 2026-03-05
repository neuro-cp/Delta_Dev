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
FORCED_STEPS   = 100

SMALL_POKE = 1.0
ASYM_POKE  = 1.0

GATE_OPEN_THRESHOLD = 0.47

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
    t0 = time.time()
    while True:
        out = send("help")
        if out and "Commands:" in out:
            return
        if time.time() - t0 > 20:
            raise RuntimeError("TCP server not responding.")
        time.sleep(0.5)

# ============================================================
# Parsing
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
# CSV INIT
# ============================================================

def init_csvs() -> None:
    with open(DOM_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id","value_mag","trial","step",
            "winner","D1","D2","delta"
        ])

    with open(DEBUG_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id","value_mag","trial","step",
            "t_runtime","winner","D1","D2",
            "delta","gate_relief",
            "decision_seen","max_delta_so_far","max_relief_so_far"
        ])

    with open(DEC_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id","trial","step","time",
            "winner","delta_dominance","relief"
        ])

# ============================================================
# LOGGING
# ============================================================

def log_step(
    run_id: int,
    trial: int,
    step: int,
    t: float,
    winner: str,
    d1: float,
    d2: float,
    delta: float,
    gate: Optional[float],
    decision_seen: int,
    max_delta: float,
    max_relief: float,
) -> None:

    with open(DOM_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            run_id, 0.0, trial, step,
            winner, d1, d2, delta
        ])

    with open(DEBUG_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            run_id, 0.0, trial, step,
            t, winner, d1, d2,
            delta, gate,
            decision_seen, max_delta, max_relief
        ])

# ============================================================
# MAIN SUITE
# ============================================================

def main() -> None:
    print("=== STRIATUM ASYMMETRY + GATE TEST SUITE ===")

    init_csvs()
    wait_for_server()
    send("reset_latch")

    run_id = 1
    trial  = 1
    step   = 0

    max_delta  = 0.0
    max_relief = 0.0
    decision_seen = 0

    gate_opened = False

    
    # ---------------------------
    # TEST 3/4 — Gate-triggered forced decision
    # ---------------------------
    print("[TEST 3/4] Gate-triggered forced win")

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

        # Edge-triggered gate opening
        if gate is not None and gate >= GATE_OPEN_THRESHOLD and not gate_opened:
            gate_opened = True
            send(f"poke striatum:D1_MSN {ASYM_POKE}", expect_reply=False)

        dec = send("decision")
        if dec.startswith("DECISION:") and "none" not in dec:
            decision_seen = 1
            with open(DEC_CSV, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    run_id, trial, step, t,
                    winner, delta, gate
                ])
            break

        log_step(
            run_id, trial, step, t,
            winner, d1, d2, delta,
            gate, decision_seen,
            max_delta, max_relief
        )

        step += 1

    print("=== SUITE COMPLETE ===")

if __name__ == "__main__":
    main()
