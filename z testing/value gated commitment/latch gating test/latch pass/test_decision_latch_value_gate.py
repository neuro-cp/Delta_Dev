from __future__ import annotations

import socket
import time
import csv
import re
from pathlib import Path
from typing import Optional, Dict, Tuple, Any

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
LOG_PATH = BASE_DIR / "runtime_log.txt"

DOM_CSV_PATH = BASE_DIR / "dominance_trace.csv"
DECISION_CSV_PATH = BASE_DIR / "decision_latch_trace.csv"
DEBUG_CSV_PATH = BASE_DIR / "decision_debug_trace.csv"   # always written (per-step)

DT = 0.01

BASELINE_WAIT = 6.0
INTEGRATION_STEPS = 25
DECAY_WAIT = 4.0

SMALL_POKE = 1.0

# -------------------------
# Value signal (dopamine)
# -------------------------
VALUE_REGION = "vta"     # or "snc"
VALUE_MAG = 0.75        # intentionally small
VALUE_STEP = 10         # when value arrives

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
        csv.writer(f).writerow(["step", "winner", "D1", "D2", "delta"])

    # Fires once (only if decision latch fires)
    with open(DECISION_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step",
            "time",
            "winner",
            "delta_dominance",
            "relief",
        ])

    # Always written (per-step) so pandaplot can *always* show something
    with open(DEBUG_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step",
            "t_runtime",
            "winner",
            "D1",
            "D2",
            "delta",
            "gate_relief",
            "decision_seen",
            "raw_striatum_len",
            "raw_gate_len",
            "raw_decision_len",
        ])

def append_dom_csv(step: int, winner: str, d1: float, d2: float) -> None:
    with open(DOM_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([step, winner, d1, d2, abs(d1 - d2)])

def append_decision_csv(step: int, decision: Dict[str, Any]) -> None:
    with open(DECISION_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            decision.get("time"),
            decision.get("winner"),
            decision.get("delta_dominance"),
            decision.get("relief"),
        ])

def append_debug_csv(
    step: int,
    t_runtime: float,
    winner: str,
    d1: float,
    d2: float,
    relief: Optional[float],
    decision_seen: bool,
    raw_striatum: str,
    raw_gate: str,
    raw_decision: str,
) -> None:
    with open(DEBUG_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            t_runtime,
            winner,
            d1,
            d2,
            abs(d1 - d2),
            "" if relief is None else relief,
            int(decision_seen),
            len(raw_striatum or ""),
            len(raw_gate or ""),
            len(raw_decision or ""),
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
        log(f"[TCP ERROR] cmd='{cmd}' err={e}")
        return ""

# ============================================================
# PARSING
# ============================================================

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

# Accept BOTH:
#   D1=0.5123
#   D1 = 0.5123
#   D1: 0.5123
RE_CH_VAL = re.compile(rf"\b(D1|D2)\b\s*(?:=|:)\s*({_NUM})", re.I)

# Winner formats:
#   winner=D1
#   Winner: D1
RE_WINNER_EQ = re.compile(r"^\s*winner\s*=\s*(\w+)\s*$", re.I)
RE_WINNER_COLON = re.compile(r"^\s*Winner\s*:\s*(\w+)\s*$", re.I)

RE_RELIEF = re.compile(rf"\brelief\s*=\s*({_NUM})", re.I)
RE_DECISION_FIELD = re.compile(r"\s*(\w+)\s*=\s*(.+)")

def parse_striatum(out: str) -> Optional[Tuple[str, float, float]]:
    """
    Works with BOTH:
      - 'striatum' command (winner=D1, D1=..., D2=...)
      - 'striatum_diag' command (Winner: D1, D1: ..., D2: ...)
    """
    if not out:
        return None

    winner = ""
    d1 = None
    d2 = None

    for line in out.splitlines():
        line_stripped = line.strip()

        m = RE_WINNER_EQ.match(line_stripped)
        if m:
            winner = m.group(1).strip()
            continue

        m = RE_WINNER_COLON.match(line_stripped)
        if m:
            winner = m.group(1).strip()
            continue

        m = RE_CH_VAL.search(line_stripped)
        if m:
            ch = m.group(1).upper()
            val = float(m.group(2))
            if ch == "D1":
                d1 = val
            elif ch == "D2":
                d2 = val

    if d1 is None or d2 is None:
        return None

    return winner, d1, d2

def parse_gate_relief(out: str) -> Optional[float]:
    if not out:
        return None
    m = RE_RELIEF.search(out)
    return float(m.group(1)) if m else None

def parse_decision(out: str) -> Optional[Dict[str, Any]]:
    if not out:
        return None
    if not out.startswith("DECISION:"):
        return None
    if out.strip() == "DECISION: none":
        return None

    data: Dict[str, Any] = {}
    for line in out.splitlines()[1:]:
        m = RE_DECISION_FIELD.match(line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        # Try float; otherwise keep as string
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
    log(f"[POKE] {region} {mag}")

# ============================================================
# MAIN — DECISION LATCH VALUE-GATED TEST (DEBUG)
# ============================================================

log("=== BEGIN DECISION LATCH VALUE-GATED TEST (DEBUG) ===")
init_csvs()

decision_seen = False
step = 0

max_delta = 0.0
max_relief = 0.0

log("[BASELINE]")
time.sleep(BASELINE_WAIT)

for i in range(1, INTEGRATION_STEPS + 1):
    poke("striatum", SMALL_POKE)

    if i == VALUE_STEP:
        log(f"[VALUE] Injecting value via {VALUE_REGION} ({VALUE_MAG})")
        poke(VALUE_REGION, VALUE_MAG)

    # Let the runtime integrate
    time.sleep(DT * 25)

    # IMPORTANT: use 'striatum' (equals format) — easiest + stable
    raw_striatum = send("striatum")
    parsed = parse_striatum(raw_striatum)

    if not parsed:
        # Fallback: maybe your server only exposes diag nicely
        raw_diag = send("striatum_diag")
        parsed = parse_striatum(raw_diag)
        if not parsed:
            log("[WARN] Could not parse striatum dominance.")
            log(f"[RAW striatum] {raw_striatum[:400]}")
            log(f"[RAW striatum_diag] {raw_diag[:400]}")
            continue
        else:
            raw_striatum = raw_diag

    winner, d1, d2 = parsed
    delta = abs(d1 - d2)
    max_delta = max(max_delta, delta)

    raw_gate = send("gate")
    relief = parse_gate_relief(raw_gate)
    if relief is not None:
        max_relief = max(max_relief, relief)

    append_dom_csv(step, winner, d1, d2)

    raw_decision = ""
    if not decision_seen:
        raw_decision = send("decision")
        decision = parse_decision(raw_decision)
        if decision:
            decision_seen = True
            append_decision_csv(step, decision)
            log(
                f"[DECISION] winner={decision.get('winner')} "
                f"Δ={float(decision.get('delta_dominance', 0.0)):.4f} "
                f"relief={float(decision.get('relief', 0.0)):.4f} "
                f"t={float(decision.get('time', 0.0)):.3f}"
            )
        elif raw_decision and raw_decision.strip() != "DECISION: none":
            log(f"[WARN] decision returned unexpected:\n{raw_decision}")

    # Always write a per-step debug row
    t_runtime = float(i) * DT * 25.0
    append_debug_csv(
        step=step,
        t_runtime=t_runtime,
        winner=winner,
        d1=d1,
        d2=d2,
        relief=relief,
        decision_seen=decision_seen,
        raw_striatum=raw_striatum,
        raw_gate=raw_gate,
        raw_decision=raw_decision,
    )

    step += 1

log("[DECAY]")
time.sleep(DECAY_WAIT)

log(f"=== TEST COMPLETE === max_delta={max_delta:.6f} max_relief={max_relief:.6f} decision_seen={decision_seen} ===")
