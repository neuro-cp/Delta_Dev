from __future__ import annotations

import csv
import re
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

OUT_DIR = Path(__file__).resolve().parent / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TS = time.strftime("%Y%m%d_%H%M%S")
LOG_PATH = OUT_DIR / f"tcp_value_gate_audit_{TS}.txt"
CSV_PATH = OUT_DIR / f"tcp_value_gate_audit_{TS}.csv"

SAMPLE_DT = 0.20  # seconds between samples

BASELINE_S = 6.0
VALUE_HOLD_S = 10.0
CLEAR_HOLD_S = 10.0

TARGET_VALUE = 0.78

# ============================================================
# TCP helpers
# ============================================================

def send(cmd: str, timeout: float = 1.0) -> str:
    data = (cmd.strip() + "\n").encode("utf-8")
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.sendall(data)
        out = s.recv(4096).decode("utf-8", errors="replace")
    return out.strip()

def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============================================================
# Parsers (robust to formatting changes)
# ============================================================

RE_VALUE = re.compile(r"VALUE:\s*([0-9]*\.?[0-9]+)")
RE_GATE = re.compile(r"relief=([0-9]*\.?[0-9]+)")
RE_DOM  = re.compile(r"^(D1|D2)\s*=\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
RE_DOM2 = re.compile(r"^(D1|D2)\s*=\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)

# Stats output format might vary. We'll try to extract a "mean" float if present.
RE_MEAN = re.compile(r"mean[^0-9]*([0-9]*\.?[0-9]+)", re.IGNORECASE)

def parse_value(raw: str) -> Optional[float]:
    m = RE_VALUE.search(raw)
    return float(m.group(1)) if m else None

def parse_gate_relief(raw: str) -> Optional[float]:
    m = RE_GATE.search(raw)
    return float(m.group(1)) if m else None

def parse_striatum_d1d2(raw: str) -> Tuple[Optional[float], Optional[float], str]:
    d1 = None
    d2 = None
    winner = ""
    # The server prints STRIATUM lines like:
    # winner=D2
    # D2=0.123456
    # D1=0.123123
    for line in raw.splitlines():
        line = line.strip()
        if line.lower().startswith("winner="):
            winner = line.split("=", 1)[1].strip()
        if line.upper().startswith("D1="):
            try: d1 = float(line.split("=", 1)[1])
            except: pass
        if line.upper().startswith("D2="):
            try: d2 = float(line.split("=", 1)[1])
            except: pass
    return d1, d2, winner

def parse_stats_mean(raw: str) -> Optional[float]:
    m = RE_MEAN.search(raw)
    return float(m.group(1)) if m else None

def parse_control_phase(raw: str) -> str:
    # control dump is JSON-ish; just grab `"phase": "..."`
    m = re.search(r'"phase"\s*:\s*"([^"]+)"', raw)
    return m.group(1) if m else ""

# ============================================================
# Sampling
# ============================================================

@dataclass
class Sample:
    wall_s: float
    phase: str
    value: Optional[float]
    gate_relief: Optional[float]
    gpi_mean: Optional[float]
    d1: Optional[float]
    d2: Optional[float]
    delta: Optional[float]
    winner: str
    control_phase: str

def take_sample(phase: str, t0: float) -> Sample:
    raw_value = send("value")
    raw_gate = send("gate")
    raw_gpi  = send("stats gpi")
    raw_stri = send("striatum")
    raw_ctl  = send("control")

    v = parse_value(raw_value)
    gr = parse_gate_relief(raw_gate)
    gpi_mean = parse_stats_mean(raw_gpi)

    d1, d2, win = parse_striatum_d1d2(raw_stri)
    delta = abs(d1 - d2) if (d1 is not None and d2 is not None) else None
    cphase = parse_control_phase(raw_ctl)

    return Sample(
        wall_s=time.time() - t0,
        phase=phase,
        value=v,
        gate_relief=gr,
        gpi_mean=gpi_mean,
        d1=d1,
        d2=d2,
        delta=delta,
        winner=win,
        control_phase=cphase,
    )

def run_phase(name: str, duration_s: float, t0: float) -> list[Sample]:
    log(f"[PHASE] {name} for {duration_s:.1f}s @ dt={SAMPLE_DT:.2f}s")
    out: list[Sample] = []
    t_end = time.time() + duration_s
    i = 0
    while time.time() < t_end:
        s = take_sample(name, t0)
        out.append(s)
        if i % 5 == 0:
            log(
                f"[{name} {i:04d}] value={s.value} gate_relief={s.gate_relief} "
                f"gpi_mean={s.gpi_mean} Δ={s.delta} winner={s.winner} control={s.control_phase}"
            )
        i += 1
        time.sleep(SAMPLE_DT)
    return out

def write_csv(samples: list[Sample]) -> None:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "wall_s","phase","value","gate_relief","gpi_mean",
            "d1","d2","delta","winner","control_phase"
        ])
        for s in samples:
            w.writerow([
                f"{s.wall_s:.3f}",
                s.phase,
                "" if s.value is None else f"{s.value:.6f}",
                "" if s.gate_relief is None else f"{s.gate_relief:.6f}",
                "" if s.gpi_mean is None else f"{s.gpi_mean:.6f}",
                "" if s.d1 is None else f"{s.d1:.6f}",
                "" if s.d2 is None else f"{s.d2:.6f}",
                "" if s.delta is None else f"{s.delta:.6f}",
                s.winner,
                s.control_phase,
            ])

def main() -> None:
    log("=== BEGIN: TCP Value -> Gate Audit (Baseline vs Value vs Clear) ===")
    log(f"Target: {HOST}:{PORT}")

    # Clean slate
    log("[CLEAN] reset_latch + value_clear")
    log(send("reset_latch"))
    log(send("value_clear"))

    # Sanity: show help header line
    h = send("help")
    log("HELP first lines:\n" + "\n".join(h.splitlines()[:8]))

    t0 = time.time()
    samples: list[Sample] = []

    # Phase A: Baseline drift
    samples += run_phase("baseline", BASELINE_S, t0)

    # Phase B: Set value once and hold
    log(f"[ACTION] value_set {TARGET_VALUE}")
    log(send(f"value_set {TARGET_VALUE}"))
    samples += run_phase("value_hold", VALUE_HOLD_S, t0)

    # Phase C: Clear value and hold
    log("[ACTION] value_clear")
    log(send("value_clear"))
    samples += run_phase("clear_hold", CLEAR_HOLD_S, t0)

    write_csv(samples)

    log("=== END ===")
    log(f"Outputs:\n  {LOG_PATH}\n  {CSV_PATH}")
    log("Interpretation:")
    log("  - If value changes but gate_relief/gpi_mean curves are statistically the same as baseline drift → value is wired but not influencing gate (expected).")
    log("  - If value changes AND gpi_mean shifts consistently relative to baseline → you have an indirect coupling path worth auditing.")
    log("  - If stats gpi doesn't include mean, we’ll still have raw outputs in the log to adjust the parser.")

if __name__ == "__main__":
    main()
