from __future__ import annotations

import socket
import time
import csv
import re
from pathlib import Path
from typing import Optional, Tuple, Dict

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
DECAY_WAIT = 4.0

HOOK_STEPS = 25
HOOK_WAIT = DT * HOOK_STEPS

SMALL_POKE = 1.0

DELTA_COMMIT = 0.02
GATE_COMMIT = 0.55

# -------------------------
# Controlled bias
# -------------------------
BIAS_POKE_STEP = 1
BIAS_REGION = "striatum"
BIAS_MAG = 0.3

# -------------------------
# Experiments
# -------------------------
EXPERIMENTS = [
    ("CONTROL", None),
    ("BIAS_D1", "D1"),
    ("BIAS_D2", "D2"),
]

STEPS_PER_EXPERIMENT = 1000

# ============================================================
# LOGGING
# ============================================================

def log(line: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{ts}] {line}"
    print(msg)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# ============================================================
# CSV
# ============================================================

def init_csvs() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)

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
# DECISION SNAPSHOT
# ============================================================

_committed = False

def snap_decision_step(tag: str, step: int) -> bool:
    global _committed

    diag = send("striatum_diag")
    parsed = parse_striatum_diag(diag)
    if not parsed:
        return False

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
        log(f"[COMMIT] {tag} winner={winner} Δ={delta:.4f} relief={relief:.4f}")

    append_dom_csv(step, winner, d1, d2)
    append_decision_csv(step, winner, d1, d2, gpi, relief, commit)

    return commit

# ============================================================
# INPUT
# ============================================================

def poke(region: str, mag: float) -> None:
    send(f"poke {region} {mag}", expect_reply=False)
    log(f"[POKE] {region} {mag}")

# ============================================================
# MAIN — THREE EXPERIMENTS
# ============================================================

log("=== BEGIN MULTI-EXPERIMENT DECISION TEST ===")
init_csvs()

global_step = 0

for name, bias in EXPERIMENTS:
    log(f"\n=== EXPERIMENT: {name} ===")
    _committed = False

    log("[BASELINE]")
    time.sleep(BASELINE_WAIT)
    snap_decision_step(f"{name}_baseline", global_step)

    log("[INTEGRATION]")
    for i in range(1, 21):
        if not _committed:
            poke("striatum", SMALL_POKE)

            if bias and i == BIAS_POKE_STEP:
                log(f"[BIAS] {bias} mag={BIAS_MAG}")
                poke(BIAS_REGION, BIAS_MAG)

        time.sleep(HOOK_WAIT)

        if i % 5 == 0:
            global_step += 1
            snap_decision_step(f"{name}_integrate_{i}", global_step)

    log("[DECAY]")
    time.sleep(DECAY_WAIT)
    global_step += 1
    snap_decision_step(f"{name}_decay", global_step)

    log("[NORMALIZATION]")
    time.sleep(BASELINE_WAIT + DECAY_WAIT)

log("=== ALL EXPERIMENTS COMPLETE ===")
