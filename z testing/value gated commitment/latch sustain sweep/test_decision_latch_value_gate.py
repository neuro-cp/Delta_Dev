from __future__ import annotations

import socket
import time
import csv
import re
from pathlib import Path
from typing import Optional, Dict, Tuple, Any, List

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")

LOG_PATH = BASE_DIR / "runtime_log.txt"
DOM_CSV_PATH = BASE_DIR / "dominance_trace.csv"
DECISION_CSV_PATH = BASE_DIR / "decision_latch_trace.csv"
DEBUG_CSV_PATH = BASE_DIR / "decision_debug_trace.csv"

DT = 0.01
BASELINE_WAIT = 6.0
INTEGRATION_STEPS = 30
DECAY_WAIT = 4.0

SMALL_POKE = 1.0
VALUE_REGION = "vta"
VALUE_STEP = 10

# -------------------------
# EXPERIMENT B (SUSTAIN SWEEP)
# -------------------------
# Fix VALUE_MAG so sustain is the manipulated variable.
VALUE_MAG_FIXED = 0.75
TRIALS_PER_SUSTAIN = 6
SUSTAIN_SWEEP: List[int] = [2, 3, 4, 5, 6, 8]

# Poll period (kept consistent with prior harness)
POLL_TICKS = 25            # runtime steps per poll (empirically matches your cadence)
POLL_SLEEP = DT * POLL_TICKS

# ============================================================
# LOGGING
# ============================================================

def log(line: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {line}"
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# ============================================================
# CSV INIT
# ============================================================

def init_csvs() -> None:
    # Dominance trace (same core columns, add sustain)
    with open(DOM_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id",
            "sustain_steps",
            "value_mag",
            "trial",
            "step",
            "winner",
            "D1",
            "D2",
            "delta",
        ])

    # Decision latch trace (same core columns, add sustain)
    with open(DECISION_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id",
            "sustain_steps",
            "value_mag",
            "trial",
            "step",
            "time",
            "winner",
            "delta_dominance",
            "relief",
        ])

    # Debug trace (keep your rejection diagnostics + sustain)
    with open(DEBUG_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id",
            "sustain_steps",
            "value_mag",
            "trial",
            "step",
            "t_runtime",
            "winner",
            "D1",
            "D2",
            "delta",
            "gate_relief",
            "decision_seen",
            "max_delta_so_far",
            "max_relief_so_far",
        ])

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
        log(f"[TCP ERROR] {cmd} :: {e}")
        return ""

# ============================================================
# PARSING
# ============================================================

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

RE_VAL = re.compile(rf"\b(D1|D2)\b\s*(?:=|:)\s*({_NUM})", re.I)
RE_WIN = re.compile(r"(winner|Winner)\s*(?:=|:)\s*(\w+)", re.I)
RE_RELIEF = re.compile(rf"relief\s*=\s*({_NUM})", re.I)
RE_FIELD = re.compile(r"\s*(\w+)\s*=\s*(.+)")

def parse_striatum(out: str) -> Optional[Tuple[str, float, float]]:
    if not out:
        return None

    winner = ""
    d1 = d2 = None

    for line in out.splitlines():
        if m := RE_WIN.search(line):
            winner = m.group(2)
        if m := RE_VAL.search(line):
            if m.group(1).upper() == "D1":
                d1 = float(m.group(2))
            else:
                d2 = float(m.group(2))

    if d1 is None or d2 is None:
        return None

    return winner, d1, d2

def parse_relief(out: str) -> Optional[float]:
    if not out:
        return None
    m = RE_RELIEF.search(out)
    return float(m.group(1)) if m else None

def parse_decision(out: str) -> Optional[Dict[str, Any]]:
    if not out or not out.startswith("DECISION:") or out.strip() == "DECISION: none":
        return None

    data: Dict[str, Any] = {}
    for line in out.splitlines()[1:]:
        if m := RE_FIELD.match(line):
            k, v = m.group(1), m.group(2)
            try:
                data[k] = float(v)
            except Exception:
                data[k] = v

    return data if data else None

# ============================================================
# INPUT
# ============================================================

def poke(region: str, mag: float) -> None:
    send(f"poke {region} {mag}", expect_reply=False)

# ============================================================
# LATCH CONTROL (Part B)
# ============================================================

def set_sustain(n: int) -> None:
    # New server feature: "sustain <N>"
    send(f"sustain {int(n)}")

def reset_latch() -> None:
    # New server feature: "reset_latch"
    send("reset_latch")

# ============================================================
# MAIN EXPERIMENT LOOP (B)
# ============================================================

log("=== BEGIN DECISION LATCH SUSTAIN SWEEP (PART B) ===")
init_csvs()

run_id = 0

for sustain_steps in SUSTAIN_SWEEP:
    log(f"[BLOCK] sustain_steps={sustain_steps} value_mag={VALUE_MAG_FIXED}")

    # Set sustain requirement once per block
    set_sustain(sustain_steps)

    for trial in range(1, TRIALS_PER_SUSTAIN + 1):
        run_id += 1
        log(f"[RUN {run_id}] SUSTAIN={sustain_steps} VALUE_MAG={VALUE_MAG_FIXED} TRIAL={trial}")

        # Reset the one-shot latch per trial (does not touch dynamics)
        reset_latch()

        decision_seen = False
        step = 0

        max_delta = 0.0
        max_relief = 0.0

        time.sleep(BASELINE_WAIT)

        for i in range(1, INTEGRATION_STEPS + 1):
            poke("striatum", SMALL_POKE)

            if i == VALUE_STEP:
                poke(VALUE_REGION, VALUE_MAG_FIXED)

            time.sleep(POLL_SLEEP)

            parsed = parse_striatum(send("striatum"))
            if not parsed:
                continue

            winner, d1, d2 = parsed
            delta = abs(d1 - d2)
            relief = parse_relief(send("gate"))

            if delta > max_delta:
                max_delta = delta
            if relief is not None and relief > max_relief:
                max_relief = relief

            # Dominance trace
            with open(DOM_CSV_PATH, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    run_id,
                    sustain_steps,
                    VALUE_MAG_FIXED,
                    trial,
                    step,
                    winner,
                    d1,
                    d2,
                    delta,
                ])

            # Decision event (first hit only)
            if not decision_seen:
                dec = parse_decision(send("decision"))
                if dec:
                    decision_seen = True
                    with open(DECISION_CSV_PATH, "a", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerow([
                            run_id,
                            sustain_steps,
                            VALUE_MAG_FIXED,
                            trial,
                            step,
                            dec.get("time"),
                            dec.get("winner"),
                            dec.get("delta_dominance"),
                            dec.get("relief"),
                        ])

            # Debug trace
            with open(DEBUG_CSV_PATH, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    run_id,
                    sustain_steps,
                    VALUE_MAG_FIXED,
                    trial,
                    step,
                    i * POLL_SLEEP,     # consistent with polling cadence
                    winner,
                    d1,
                    d2,
                    delta,
                    relief,
                    int(decision_seen),
                    max_delta,
                    max_relief,
                ])

            step += 1

        time.sleep(DECAY_WAIT)

log("=== EXPERIMENT COMPLETE ===")
