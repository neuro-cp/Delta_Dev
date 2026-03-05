from __future__ import annotations

import socket
import time
import csv
import re
from pathlib import Path
from typing import Optional, Dict, Tuple

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
LOG_PATH = BASE_DIR / "runtime_log.txt"

DOM_CSV_PATH = BASE_DIR / "dominance_trace.csv"
DECISION_CSV_PATH = BASE_DIR / "decision_gating_trace.csv"

DT = 0.01

BASELINE_WAIT = 6.0
INTEGRATION_STEPS = 25
DECAY_WAIT = 4.0

SMALL_POKE = 1.0

DELTA_COMMIT = 0.02
GATE_COMMIT = 0.55

# -------------------------
# Value signal (dopamine)
# -------------------------
VALUE_REGION = "vta"      # or "snc"
VALUE_MAG = 0.25          # intentionally small
VALUE_STEP = 10           # when value arrives

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
# CSV
# ============================================================

def init_csvs() -> None:
    with open(DOM_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["step", "winner", "D1", "D2"])

    with open(DECISION_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step", "winner", "D1", "D2",
            "gpi_mass", "gpi_mean", "gpi_std", "gpi_n",
            "gate_relief", "commit"
        ])

def append_dom_csv(step: int, winner: str, d1: float, d2: float) -> None:
    with open(DOM_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([step, winner, d1, d2])

def append_decision_csv(
    step: int,
    winner: str,
    d1: float,
    d2: float,
    gpi: Optional[Dict[str, float]],
    gate_relief: Optional[float],
    commit: bool,
) -> None:
    with open(DECISION_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            winner,
            d1,
            d2,
            "" if not gpi else gpi["mass"],
            "" if not gpi else gpi["mean"],
            "" if not gpi else gpi["std"],
            "" if not gpi else gpi["n"],
            "" if gate_relief is None else gate_relief,
            int(commit),
        ])

# ============================================================
# TCP
# ============================================================

def send(cmd: str, expect_reply: bool = True) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
            sock.sendall((cmd.strip() + "\n").encode())
            if not expect_reply:
                return ""
            return sock.recv(16384).decode(errors="replace").strip()
    except Exception:
        return ""

# ============================================================
# PARSING
# ============================================================

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

RE_STAT = re.compile(
    rf"\S+\s+MASS=({_NUM})\s+MEAN=({_NUM})\s+STD=({_NUM})\s+N=(\d+)"
)
RE_RELIEF = re.compile(rf"relief=({_NUM})", re.I)

def parse_striatum_diag(out: str) -> Optional[Tuple[str, float, float]]:
    d1 = d2 = None
    winner = ""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("D1:"):
            d1 = float(line.split(":")[1])
        elif line.startswith("D2:"):
            d2 = float(line.split(":")[1])
        elif line.startswith("Winner:"):
            winner = line.split(":")[1].strip()
    if d1 is None or d2 is None:
        return None
    return winner, d1, d2

def parse_region_stats(out: str) -> Optional[Dict[str, float]]:
    m = RE_STAT.search(out)
    if not m:
        return None
    return {
        "mass": float(m.group(1)),
        "mean": float(m.group(2)),
        "std": float(m.group(3)),
        "n": int(m.group(4)),
    }

def parse_gate_relief(out: str) -> Optional[float]:
    m = RE_RELIEF.search(out)
    return float(m.group(1)) if m else None

# ============================================================
# INPUT
# ============================================================

def poke(region: str, mag: float) -> None:
    send(f"poke {region} {mag}", expect_reply=False)
    log(f"[POKE] {region} {mag}")

# ============================================================
# MAIN — VALUE-GATED DECISION TEST
# ============================================================

log("=== BEGIN VALUE-GATED DECISION TEST ===")
init_csvs()

_committed = False
step = 0

log("[BASELINE]")
time.sleep(BASELINE_WAIT)

for i in range(1, INTEGRATION_STEPS + 1):
    poke("striatum", SMALL_POKE)

    # -------------------------
    # VALUE ARRIVAL
    # -------------------------
    if i == VALUE_STEP:
        log(f"[VALUE] Injecting value via {VALUE_REGION} ({VALUE_MAG})")
        poke(VALUE_REGION, VALUE_MAG)

    time.sleep(DT * 25)

    diag = send("striatum_diag")
    parsed = parse_striatum_diag(diag)
    if not parsed:
        continue

    winner, d1, d2 = parsed
    delta = abs(d1 - d2)

    gpi = parse_region_stats(send("stats gpi"))
    relief = parse_gate_relief(send("gate"))

    commit = (
        not _committed
        and relief is not None
        and delta >= DELTA_COMMIT
        and relief >= GATE_COMMIT
    )

    if commit:
        _committed = True
        log(f"[COMMIT] winner={winner} Δ={delta:.4f} relief={relief:.4f}")

    append_dom_csv(step, winner, d1, d2)
    append_decision_csv(step, winner, d1, d2, gpi, relief, commit)

    step += 1

log("[DECAY]")
time.sleep(DECAY_WAIT)

log("=== TEST COMPLETE ===")
