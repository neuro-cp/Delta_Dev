from __future__ import annotations

import csv
import re
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

HOST = "127.0.0.1"
PORT = 5557

OUT_DIR = Path(__file__).resolve().parent / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TS = time.strftime("%Y%m%d_%H%M%S")
LOG_PATH = OUT_DIR / f"tcp_value_gate_abab_{TS}.txt"
CSV_PATH = OUT_DIR / f"tcp_value_gate_abab_{TS}.csv"

DT = 0.20

# Phases
SETTLE_S = 20.0
A_S = 10.0          # value OFF
RAMP_CALLS = 10     # value_set 0.78 repeatedly to reach plateau (policy-limited ~+0.1/call)
RAMP_SLEEP = 0.12   # respects min_interval
B_HOLD_S = 10.0     # value ON plateau-ish
A2_S = 10.0
B2_HOLD_S = 10.0

TARGET_VALUE = 0.78

RE_VALUE = re.compile(r"VALUE:\s*([0-9]*\.?[0-9]+)")
RE_RELIEF = re.compile(r"relief=([0-9]*\.?[0-9]+)")
RE_MEAN = re.compile(r"mean[^0-9]*([0-9]*\.?[0-9]+)", re.IGNORECASE)

def send(cmd: str, timeout: float = 1.0) -> str:
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.sendall((cmd.strip() + "\n").encode("utf-8"))
        return s.recv(8192).decode("utf-8", errors="replace").strip()

def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def parse_value(raw: str) -> Optional[float]:
    m = RE_VALUE.search(raw)
    return float(m.group(1)) if m else None

def parse_relief(raw: str) -> Optional[float]:
    m = RE_RELIEF.search(raw)
    return float(m.group(1)) if m else None

def parse_mean(raw: str) -> Optional[float]:
    m = RE_MEAN.search(raw)
    return float(m.group(1)) if m else None

def control_phase(raw: str) -> str:
    m = re.search(r'"phase"\s*:\s*"([^"]+)"', raw)
    return m.group(1) if m else ""

@dataclass
class Sample:
    t_wall: float
    phase: str
    value: Optional[float]
    gate_relief: Optional[float]
    gpi_mean: Optional[float]
    phase_name: str

def take_sample(phase: str, phase_name: str, t0: float) -> Sample:
    raw_value = send("value")
    raw_gate = send("gate")
    raw_gpi = send("stats gpi")
    raw_ctl = send("control")

    v = parse_value(raw_value)
    relief = parse_relief(raw_gate)
    gpi_mean = parse_mean(raw_gpi)

    ph = control_phase(raw_ctl)
    if ph and ph != "pre-decision":
        log(f"[WARN] control phase is {ph} during {phase_name} (expected pre-decision)")

    return Sample(
        t_wall=time.time() - t0,
        phase=phase,
        value=v,
        gate_relief=relief,
        gpi_mean=gpi_mean,
        phase_name=phase_name,
    )

def run_window(label: str, duration_s: float, t0: float, samples: List[Sample]) -> None:
    log(f"[PHASE] {label} for {duration_s:.1f}s")
    t_end = time.time() + duration_s
    i = 0
    while time.time() < t_end:
        s = take_sample(label, label, t0)
        samples.append(s)
        if i % 5 == 0:
            log(f"[{label} {i:04d}] value={s.value} relief={s.gate_relief} gpi_mean={s.gpi_mean}")
        i += 1
        time.sleep(DT)

def slope(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    x0 = xs[0]
    x = [t - x0 for t in xs]
    n = len(x)
    sx = sum(x)
    sy = sum(ys)
    sxx = sum(t*t for t in x)
    sxy = sum(x[i]*ys[i] for i in range(n))
    denom = (n * sxx - sx * sx)
    if abs(denom) < 1e-12:
        return None
    return (n * sxy - sx * sy) / denom

def summarize(samples: List[Sample], phase_name: str) -> Tuple[Optional[float], Optional[float]]:
    ss = [s for s in samples if s.phase == phase_name and s.gate_relief is not None]
    if len(ss) < 3:
        return None, None
    xs = [s.t_wall for s in ss]
    ys = [float(s.gate_relief) for s in ss]
    return sum(ys)/len(ys), slope(xs, ys)

def main() -> None:
    log("=== BEGIN: Value/Gate ABAB Plateau Test ===")
    log("[CLEAN] reset_latch + value_clear")
    log(send("reset_latch"))
    log(send("value_clear"))

    t0 = time.time()
    samples: List[Sample] = []

    # Settle
    run_window("settle", SETTLE_S, t0, samples)

    # A
    log("[A] value_clear (ensure OFF)")
    log(send("value_clear"))
    run_window("A", A_S, t0, samples)

    # B ramp + hold
    log(f"[B] ramp to {TARGET_VALUE} via {RAMP_CALLS} calls")
    for i in range(RAMP_CALLS):
        log(send(f"value_set {TARGET_VALUE}"))
        time.sleep(RAMP_SLEEP)
    run_window("B", B_HOLD_S, t0, samples)

    # A2
    log("[A2] value_clear")
    log(send("value_clear"))
    run_window("A2", A2_S, t0, samples)

    # B2 (repeat ramp quickly then hold)
    log(f"[B2] ramp to {TARGET_VALUE} via {RAMP_CALLS} calls")
    for i in range(RAMP_CALLS):
        log(send(f"value_set {TARGET_VALUE}"))
        time.sleep(RAMP_SLEEP)
    run_window("B2", B2_HOLD_S, t0, samples)

    # CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_wall", "phase", "value", "gate_relief", "gpi_mean"])
        for s in samples:
            w.writerow([f"{s.t_wall:.3f}", s.phase, s.value, s.gate_relief, s.gpi_mean])

    # Summaries
    for ph in ["A", "B", "A2", "B2"]:
        mean_rel, sl = summarize(samples, ph)
        log(f"[SUMMARY {ph}] mean_relief={mean_rel} slope_relief={sl}")

    log("=== END ===")
    log(f"Outputs:\n  {LOG_PATH}\n  {CSV_PATH}")
    log("Interpretation:")
    log("  - If B and B2 consistently shift mean_relief or slope relative to A and A2 → real indirect coupling.")
    log("  - If A/A2 and B/B2 look the same within noise → value is effectively non-gate (as designed).")

if __name__ == "__main__":
    main()
