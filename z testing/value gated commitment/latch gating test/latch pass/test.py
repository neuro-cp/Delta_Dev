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

DECISION_CSV = BASE_DIR / "decision_latch_trace.csv"
DEBUG_CSV    = BASE_DIR / "decision_debug_trace.csv"
LOG_PATH     = BASE_DIR / "runtime_log.txt"

DT = 0.01
BASELINE_WAIT = 6.0
INTEGRATION_STEPS = 25
DECAY_WAIT = 4.0

STRIATUM_POKE = 1.0

VALUE_REGION = "vta"
VALUE_MAG = 0.25
VALUE_STEP = 10

# ============================================================
# LOGGING
# ============================================================

def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============================================================
# CSV INIT
# ============================================================

def init_csvs() -> None:
    # === Pandaplot canonical CSV ===
    with open(DECISION_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step",
            "winner",
            "D1",
            "D2",
            "gate_relief",
            "commit",
        ])

    # === Debug CSV (never plotted) ===
    with open(DEBUG_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step",
            "D1",
            "D2",
            "delta",
            "gate_relief",
            "decision_seen",
        ])

# ============================================================
# TCP
# ============================================================

def send(cmd: str) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
            sock.sendall((cmd.strip() + "\n").encode("utf-8"))
            return sock.recv(65535).decode("utf-8", errors="replace").strip()
    except Exception as e:
        log(f"[TCP ERROR] {cmd} → {e}")
        return ""

# ============================================================
# PARSING
# ============================================================

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

RE_CH = re.compile(rf"\b(D1|D2)\b\s*(?:=|:)\s*({_NUM})", re.I)
RE_WIN = re.compile(r"(?:winner\s*=|Winner\s*:)\s*(\w+)", re.I)
RE_RELIEF = re.compile(rf"\brelief\s*=\s*({_NUM})", re.I)

def parse_striatum(out: str) -> Optional[Tuple[str, float, float]]:
    if not out:
        return None

    winner = None
    d1 = None
    d2 = None

    for line in out.splitlines():
        if winner is None:
            m = RE_WIN.search(line)
            if m:
                winner = m.group(1)

        m = RE_CH.search(line)
        if m:
            ch, val = m.group(1).upper(), float(m.group(2))
            if ch == "D1":
                d1 = val
            elif ch == "D2":
                d2 = val

    if winner is None or d1 is None or d2 is None:
        return None

    return winner, d1, d2

def parse_gate_relief(out: str) -> Optional[float]:
    if not out:
        return None
    m = RE_RELIEF.search(out)
    return float(m.group(1)) if m else None

def decision_fired(out: str) -> bool:
    if not out:
        return False
    return out.startswith("DECISION:") and out.strip() != "DECISION: none"

# ============================================================
# INPUT
# ============================================================

def poke(region: str, mag: float) -> None:
    send(f"poke {region} {mag}")
    log(f"[POKE] {region} {mag}")

# ============================================================
# MAIN
# ============================================================

log("=== BEGIN DECISION LATCH VALUE-GATED TEST ===")
init_csvs()

decision_seen = False
step = 0

log("[BASELINE]")
time.sleep(BASELINE_WAIT)

for i in range(1, INTEGRATION_STEPS + 1):
    poke("striatum", STRIATUM_POKE)

    if i == VALUE_STEP:
        log(f"[VALUE] Injecting {VALUE_REGION} {VALUE_MAG}")
        poke(VALUE_REGION, VALUE_MAG)

    time.sleep(DT * 25)

    raw = send("striatum")
    parsed = parse_striatum(raw)
    if not parsed:
        raw = send("striatum_diag")
        parsed = parse_striatum(raw)
        if not parsed:
            log("[WARN] Could not parse striatum output")
            continue

    winner, d1, d2 = parsed
    delta = abs(d1 - d2)

    relief = parse_gate_relief(send("gate"))

    commit = 0
    if not decision_seen:
        if decision_fired(send("decision")):
            decision_seen = True
            commit = 1
            log(f"[COMMIT] winner={winner} Δ={delta:.4f} relief={relief:.4f}")

    # === Pandaplot CSV ===
    with open(DECISION_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            winner,
            d1,
            d2,
            relief if relief is not None else "",
            commit,
        ])

    # === Debug CSV ===
    with open(DEBUG_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            d1,
            d2,
            delta,
            relief if relief is not None else "",
            int(decision_seen),
        ])

    step += 1

log("[DECAY]")
time.sleep(DECAY_WAIT)

log("=== TEST COMPLETE ===")
