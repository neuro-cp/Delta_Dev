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
# EXPERIMENT SWEEP
# -------------------------

VALUE_MAG_SWEEP: List[float] = [0.25, 0.5, 0.75, 1.0]

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
    with open(DOM_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id",
            "value_mag",
            "step",
            "winner",
            "D1",
            "D2",
            "delta",
        ])

    with open(DECISION_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id",
            "value_mag",
            "step",
            "time",
            "winner",
            "delta_dominance",
            "relief",
        ])

    with open(DEBUG_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "run_id",
            "value_mag",
            "step",
            "t_runtime",
            "winner",
            "D1",
            "D2",
            "delta",
            "gate_relief",
            "decision_seen",
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
# MAIN EXPERIMENT LOOP
# ============================================================

log("=== BEGIN DECISION LATCH PARAMETER SWEEP ===")
init_csvs()

run_id = 0

for value_mag in VALUE_MAG_SWEEP:
    run_id += 1
    log(f"[RUN {run_id}] VALUE_MAG = {value_mag}")

    decision_seen = False
    step = 0

    time.sleep(BASELINE_WAIT)

    for i in range(1, INTEGRATION_STEPS + 1):
        poke("striatum", SMALL_POKE)

        if i == VALUE_STEP:
            poke(VALUE_REGION, value_mag)

        time.sleep(DT * 25)

        raw_str = send("striatum")
        parsed = parse_striatum(raw_str)
        if not parsed:
            continue

        winner, d1, d2 = parsed
        delta = abs(d1 - d2)

        relief = parse_relief(send("gate"))

        with open(DOM_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([run_id, value_mag, step, winner, d1, d2, delta])

        if not decision_seen:
            dec = parse_decision(send("decision"))
            if dec:
                decision_seen = True
                with open(DECISION_CSV_PATH, "a", newline="", encoding="utf-8") as f:
                    csv.writer(f).writerow([
                        run_id,
                        value_mag,
                        step,
                        dec.get("time"),
                        dec.get("winner"),
                        dec.get("delta_dominance"),
                        dec.get("relief"),
                    ])

        with open(DEBUG_CSV_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                run_id,
                value_mag,
                step,
                i * DT * 25,
                winner,
                d1,
                d2,
                delta,
                relief,
                int(decision_seen),
            ])

        step += 1

    time.sleep(DECAY_WAIT)

log("=== EXPERIMENT COMPLETE ===")
