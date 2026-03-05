from __future__ import annotations

import csv
import re
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

DT = 0.20  # sampling period (seconds)

# "Settle" is not time-based — it's slope/range based (with timeout)
SETTLE_MAX_S = 90.0
SETTLE_WINDOW_S = 6.0          # compute slope over last N seconds
SETTLE_SLOPE_EPS = 1.5e-4      # relief units per second
SETTLE_RANGE_EPS = 0.0025      # max-min relief within window

# ABABAB cycles
A_S = 10.0
B_S = 10.0
CYCLES = 3

# Value clamp behavior
TARGET_VALUE = 0.78
TARGET_TOL = 0.03              # consider plateau reached when value >= 0.75
RAMP_MAX_CALLS = 80            # max value_set calls to reach plateau
RAMP_SLEEP = 0.12              # respects policy min_interval
CLAMP_PERIOD = 0.60            # during B, refresh value every ~0.6s

OUT_DIR = Path(__file__).resolve().parent / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TS = time.strftime("%Y%m%d_%H%M%S")
LOG_PATH = OUT_DIR / f"tcp_value_gate_abab_clamped_{TS}.txt"
CSV_PATH = OUT_DIR / f"tcp_value_gate_abab_clamped_{TS}.csv"

# ============================================================
# TCP helpers
# ============================================================

def send(cmd: str, timeout: float = 1.0) -> str:
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.sendall((cmd.strip() + "\n").encode("utf-8"))
        return s.recv(16384).decode("utf-8", errors="replace").strip()

def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============================================================
# Parsing
# ============================================================

RE_VALUE = re.compile(r"VALUE:\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)
RE_RELIEF = re.compile(r"relief=([0-9]*\.?[0-9]+)", re.IGNORECASE)
RE_MEAN = re.compile(r"\bmean\b[^0-9]*([0-9]*\.?[0-9]+)", re.IGNORECASE)
RE_PHASE = re.compile(r'"phase"\s*:\s*"([^"]+)"')
RE_COMMITTED = re.compile(r'"committed"\s*:\s*(true|false)', re.IGNORECASE)
RE_DEC_WINNER = re.compile(r'"decision_winner"\s*:\s*(null|"[^"]+")', re.IGNORECASE)

def parse_float(regex: re.Pattern, raw: str) -> Optional[float]:
    m = regex.search(raw)
    return float(m.group(1)) if m else None

def parse_value(raw: str) -> Optional[float]:
    return parse_float(RE_VALUE, raw)

def parse_relief(raw: str) -> Optional[float]:
    return parse_float(RE_RELIEF, raw)

def parse_mean(raw: str) -> Optional[float]:
    return parse_float(RE_MEAN, raw)

def parse_control(raw: str) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {"phase": None, "committed": None, "decision_winner": None}
    m = RE_PHASE.search(raw)
    if m:
        out["phase"] = m.group(1)
    m = RE_COMMITTED.search(raw)
    if m:
        out["committed"] = m.group(1).lower()
    m = RE_DEC_WINNER.search(raw)
    if m:
        val = m.group(1)
        if val.lower() == "null":
            out["decision_winner"] = None
        else:
            out["decision_winner"] = val.strip('"')
    return out

# ============================================================
# Math helpers
# ============================================================

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

# ============================================================
# Sampling
# ============================================================

@dataclass
class Sample:
    t_wall: float
    phase_label: str
    value: Optional[float]
    relief: Optional[float]
    gpi_mean: Optional[float]
    control_phase: Optional[str]
    committed: Optional[str]
    decision_winner: Optional[str]

def take_sample(phase_label: str, t0: float) -> Sample:
    raw_value = send("value")
    raw_gate = send("gate")
    raw_gpi = send("stats gpi")
    raw_ctl = send("control")

    v = parse_value(raw_value)
    relief = parse_relief(raw_gate)
    gpi_mean = parse_mean(raw_gpi)
    ctl = parse_control(raw_ctl)

    return Sample(
        t_wall=time.time() - t0,
        phase_label=phase_label,
        value=v,
        relief=relief,
        gpi_mean=gpi_mean,
        control_phase=ctl.get("phase"),
        committed=ctl.get("committed"),
        decision_winner=ctl.get("decision_winner"),
    )

def window_samples(samples: List[Sample], phase_label: str) -> List[Sample]:
    return [s for s in samples if s.phase_label == phase_label and s.relief is not None]

def summarize(samples: List[Sample], phase_label: str) -> Dict[str, Optional[float]]:
    ss = window_samples(samples, phase_label)
    if len(ss) < 3:
        return {"mean_relief": None, "slope_relief": None, "mean_value": None, "mean_gpi": None}
    xs = [s.t_wall for s in ss]
    rs = [float(s.relief) for s in ss if s.relief is not None]
    vs = [float(s.value) for s in ss if s.value is not None]
    gs = [float(s.gpi_mean) for s in ss if s.gpi_mean is not None]
    mean_relief = sum(rs)/len(rs) if rs else None
    mean_value = sum(vs)/len(vs) if vs else None
    mean_gpi = sum(gs)/len(gs) if gs else None
    sl = slope(xs, rs) if rs else None
    return {"mean_relief": mean_relief, "slope_relief": sl, "mean_value": mean_value, "mean_gpi": mean_gpi}

# ============================================================
# Protocol steps
# ============================================================

def settle(samples: List[Sample], t0: float) -> None:
    log("=== SETTLE (slope + range) ===")
    start = time.time()
    buf: List[Sample] = []

    while True:
        s = take_sample("settle", t0)
        samples.append(s)
        buf.append(s)

        # Trim buffer to last SETTLE_WINDOW_S
        cutoff = s.t_wall - SETTLE_WINDOW_S
        buf = [x for x in buf if x.t_wall >= cutoff and x.relief is not None]

        if len(buf) >= max(10, int(SETTLE_WINDOW_S / DT) - 2):
            xs = [x.t_wall for x in buf]
            rs = [float(x.relief) for x in buf if x.relief is not None]
            sl = slope(xs, rs)
            r_range = (max(rs) - min(rs)) if rs else None

            if int(len(samples)) % 10 == 0:
                log(f"[settle] relief={s.relief} gpi_mean={s.gpi_mean} slope={sl} range={r_range}")

            if sl is not None and r_range is not None:
                if abs(sl) <= SETTLE_SLOPE_EPS and r_range <= SETTLE_RANGE_EPS:
                    log(f"[SETTLED] slope={sl:.6g} range={r_range:.6g} (window={SETTLE_WINDOW_S}s)")
                    return

        if (time.time() - start) >= SETTLE_MAX_S:
            log("[WARN] SETTLE MAX reached; proceeding anyway (may reduce test validity).")
            return

        time.sleep(DT)

def ensure_clean() -> None:
    log("[CLEAN] reset_latch + value_clear")
    log(send("reset_latch"))
    log(send("value_clear"))

def ramp_to_plateau(t0: float) -> None:
    """
    Repeatedly call value_set until observed value reaches near target, or timeout.
    """
    log(f"[RAMP] target={TARGET_VALUE} tol={TARGET_TOL} max_calls={RAMP_MAX_CALLS}")
    last_v = None
    for i in range(RAMP_MAX_CALLS):
        resp = send(f"value_set {TARGET_VALUE}")
        log(f"  (call {i+1:02d}) {resp}")

        # sample value immediately after call
        raw_value = send("value")
        v = parse_value(raw_value)
        last_v = v
        log(f"  -> observed value={v}")

        if v is not None and v >= (TARGET_VALUE - TARGET_TOL):
            log(f"[RAMP DONE] reached plateau-ish: value={v}")
            return

        time.sleep(RAMP_SLEEP)

    log(f"[WARN] ramp did not reach plateau; last observed value={last_v}")

def run_A(samples: List[Sample], t0: float, label: str, duration_s: float) -> None:
    log(f"[{label}] value_clear (OFF)")
    log(send("value_clear"))
    log(f"[PHASE] {label} for {duration_s:.1f}s")
    t_end = time.time() + duration_s
    i = 0
    while time.time() < t_end:
        s = take_sample(label, t0)
        samples.append(s)

        if s.committed == "true" or (s.control_phase and s.control_phase != "pre-decision"):
            log(f"[WARN] unexpected control state during {label}: phase={s.control_phase} committed={s.committed}")

        if i % 5 == 0:
            log(f"[{label} {i:04d}] value={s.value} relief={s.relief} gpi_mean={s.gpi_mean}")
        i += 1
        time.sleep(DT)

def run_B(samples: List[Sample], t0: float, label: str, duration_s: float) -> None:
    log(f"[{label}] ramp + clamp (ON)")
    ramp_to_plateau(t0)

    log(f"[PHASE] {label} for {duration_s:.1f}s (clamped every {CLAMP_PERIOD}s)")
    t_end = time.time() + duration_s
    next_clamp = time.time()
    i = 0
    while time.time() < t_end:
        now = time.time()
        if now >= next_clamp:
            # Keep pushing value back up to target
            send(f"value_set {TARGET_VALUE}")
            next_clamp = now + CLAMP_PERIOD

        s = take_sample(label, t0)
        samples.append(s)

        if s.committed == "true" or (s.control_phase and s.control_phase != "pre-decision"):
            log(f"[WARN] unexpected control state during {label}: phase={s.control_phase} committed={s.committed}")

        if i % 5 == 0:
            log(f"[{label} {i:04d}] value={s.value} relief={s.relief} gpi_mean={s.gpi_mean}")
        i += 1
        time.sleep(DT)

# ============================================================
# Main
# ============================================================

def main() -> None:
    log("=== BEGIN: Value/Gate ABABAB (Clamped Plateau + Settle-by-slope) ===")
    log(f"Target: {HOST}:{PORT}")
    ensure_clean()

    t0 = time.time()
    samples: List[Sample] = []

    # settle
    settle(samples, t0)

    # cycles
    for k in range(CYCLES):
        a = f"A{k+1}"
        b = f"B{k+1}"
        run_A(samples, t0, a, A_S)
        run_B(samples, t0, b, B_S)

    # write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "t_wall", "phase",
            "value", "gate_relief", "gpi_mean",
            "control_phase", "committed", "decision_winner"
        ])
        for s in samples:
            w.writerow([
                f"{s.t_wall:.3f}", s.phase_label,
                s.value, s.relief, s.gpi_mean,
                s.control_phase, s.committed, s.decision_winner
            ])

    # summaries
    log("=== SUMMARY (means + slopes) ===")
    phase_labels = []
    for k in range(CYCLES):
        phase_labels += [f"A{k+1}", f"B{k+1}"]

    for ph in phase_labels:
        summ = summarize(samples, ph)
        log(f"[{ph}] mean_relief={summ['mean_relief']} slope_relief={summ['slope_relief']} "
            f"mean_value={summ['mean_value']} mean_gpi={summ['mean_gpi']}")

    # paired diffs (B - preceding A)
    log("=== PAIRED DIFFS (B - A) ===")
    for k in range(CYCLES):
        A = f"A{k+1}"
        B = f"B{k+1}"
        sA = summarize(samples, A)
        sB = summarize(samples, B)
        if sA["mean_relief"] is not None and sB["mean_relief"] is not None:
            d_rel = sB["mean_relief"] - sA["mean_relief"]
        else:
            d_rel = None
        if sA["mean_gpi"] is not None and sB["mean_gpi"] is not None:
            d_gpi = sB["mean_gpi"] - sA["mean_gpi"]
        else:
            d_gpi = None
        log(f"[{B} - {A}] Δmean_relief={d_rel} Δmean_gpi={d_gpi}")

    log("=== END ===")
    log(f"Outputs:\n  {LOG_PATH}\n  {CSV_PATH}")
    log("Interpretation:")
    log("  - If ALL three cycles show B mean_relief shifting the same direction vs A, that's a real coupling.")
    log("  - If shifts are inconsistent or tiny vs drift, value is effectively non-gate pre-decision (as designed).")
    log("  - Any committed/phase!=pre-decision warnings are a bug for this test (value must not cause decisions).")

if __name__ == "__main__":
    main()
