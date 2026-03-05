from __future__ import annotations

import socket
import time
import csv
import re
from pathlib import Path
from typing import Optional, Tuple
from collections import deque

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_CSV  = BASE_DIR / "psm_near_decision_trace.csv"

DT = 0.01
POLL_TICKS = 25
POLL_SLEEP = DT * POLL_TICKS

MAX_STEPS = 300

# ------------------------------------------------------------
# Canonical latch values (DO NOT CHANGE)
# ------------------------------------------------------------
DECISION_DOM = 0.04
DECISION_REL = 0.47
DECISION_SUSTAIN = 5

# ------------------------------------------------------------
# Observer thresholds (diagnostic only)
# ------------------------------------------------------------

# Ignore initialization noise
WARMUP_STEPS = 25        # ~0.25s

# Near-decision (tight, conservative)
NEAR_DOM = 0.75 * DECISION_DOM   # 0.03
NEAR_REL = DECISION_REL - 0.01   # ~0.46

# Absolute noise floor
MIN_DELTA = 0.01

# Approach detection
HIST_LEN = 6

# ------------------------------------------------------------
# PSM parameters
# ------------------------------------------------------------
PSM_GAIN = 0.06
PSM_TARGET = "striatum"

BASELINE_POKE = 1.0

# ============================================================
# TCP
# ============================================================

def send(cmd: str, expect_reply: bool = True) -> str:
    with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
        sock.sendall((cmd.strip() + "\n").encode("utf-8"))
        if not expect_reply:
            return ""
        return sock.recv(65535).decode("utf-8", errors="replace").strip()

def wait_for_server() -> None:
    while True:
        try:
            if "Commands:" in send("help"):
                return
        except Exception:
            pass
        time.sleep(0.5)

# ============================================================
# PARSING
# ============================================================

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

RE_WIN = re.compile(r"winner\s*=\s*(\w+)", re.I)
RE_D1  = re.compile(rf"D1\s*=\s*({NUM})", re.I)
RE_D2  = re.compile(rf"D2\s*=\s*({NUM})", re.I)
RE_T   = re.compile(rf"t\s*=\s*({NUM})", re.I)
RE_REL = re.compile(rf"relief\s*=\s*({NUM})", re.I)

def parse_striatum(raw: str) -> Optional[Tuple[str, float, float, float]]:
    if not raw:
        return None
    try:
        winner = RE_WIN.search(raw).group(1)
        d1 = float(RE_D1.search(raw).group(1))
        d2 = float(RE_D2.search(raw).group(1))
        t  = float(RE_T.search(raw).group(1))
        return winner, d1, d2, t
    except Exception:
        return None

def parse_gate(raw: str) -> Optional[float]:
    if not raw:
        return None
    m = RE_REL.search(raw)
    return float(m.group(1)) if m else None

# ============================================================
# MAIN EXPERIMENT
# ============================================================

def main() -> None:
    print("=== PSM NEAR-DECISION EXPERIMENT (STABILIZED) ===")

    wait_for_server()
    send("reset_latch")

    primed = False

    delta_hist = deque(maxlen=HIST_LEN)
    gate_hist  = deque(maxlen=HIST_LEN)

    # --------------------------------------------------------
    # CSV INIT
    # --------------------------------------------------------
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step","time",
            "winner","D1","D2","delta",
            "relief",
            "near_decision",
            "psm_applied",
            # latch diagnostics snapshot
            "dom_threshold",
            "relief_threshold",
            "near_dom",
            "near_rel",
            "min_delta",
            "sustain_required"
        ])

    # --------------------------------------------------------
    # RUN LOOP
    # --------------------------------------------------------
    for step in range(MAX_STEPS):

        send(f"poke striatum {BASELINE_POKE}", expect_reply=False)
        time.sleep(POLL_SLEEP)

        gate = parse_gate(send("gate"))
        parsed = parse_striatum(send("striatum"))
        decision = send("decision")

        if parsed is None or gate is None:
            continue

        winner, d1, d2, t = parsed
        delta = abs(d1 - d2)

        delta_hist.append(delta)
        gate_hist.append(gate)

        # ----------------------------------------------------
        # Warm-up guard
        # ----------------------------------------------------
        if step < WARMUP_STEPS or len(delta_hist) < HIST_LEN:
            continue

        # ----------------------------------------------------
        # Approach detection
        # ----------------------------------------------------
        delta_rising = delta_hist[-1] > delta_hist[0]
        gate_rising  = gate_hist[-1]  > gate_hist[0]

        near_decision = (
            delta >= NEAR_DOM and
            delta >= MIN_DELTA and
            gate  >= NEAR_REL and
            delta_rising and
            gate_rising
        )

        psm_applied = False

        if near_decision and not primed:
            send(f"psm_prime {PSM_TARGET} {PSM_GAIN}")
            primed = True
            psm_applied = True
            print(f"[PSM] primed at step={step}, t={t:.3f}")

        with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                step, t,
                winner, d1, d2, delta,
                gate,
                int(near_decision),
                int(psm_applied),
                DECISION_DOM,
                DECISION_REL,
                NEAR_DOM,
                NEAR_REL,
                MIN_DELTA,
                DECISION_SUSTAIN
            ])

        if decision.startswith("DECISION:"):
            print(f"[DECISION] committed at step={step}, t={t:.3f}")
            break

    print("=== EXPERIMENT COMPLETE ===")
    print(f"Log written to: {OUT_CSV}")

if __name__ == "__main__":
    main()
