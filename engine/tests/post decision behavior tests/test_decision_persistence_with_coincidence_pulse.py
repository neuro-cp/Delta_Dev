from __future__ import annotations

import csv
import re
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

"""
TEST: Decision persistence with a "coincidence pulse" — TCP-driven version

This aligns with the *purpose* of your newer in-process test:
  - Baseline settle
  - Structural asymmetry / evidence ramp (best-effort via association cortex assembly targeting)
  - A short coincidence pulse (striatal poke + temporary value authorization)
  - Observe whether decision fires (acceptable if not)
  - If decision fires: observe post-decision persistence with NO stimulus

But it uses the same machinery as the old reliable test:
  - TCP command server (test_runtime.py or equivalent) must already be running
  - Commands like: poke, striatum, gate, decision, control, etc.

IMPORTANT:
  1) Start your runtime server first (e.g., run test_runtime.py that opens PORT 5557).
  2) Then run this test script from a separate terminal.
"""

# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_DIR = BASE_DIR / "engine" / "tests" / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = OUT_DIR / "tcp_coincidence_persistence_log.txt"
DEBUG_CSV_PATH = OUT_DIR / "tcp_coincidence_persistence_debug.csv"
DECISION_CSV_PATH = OUT_DIR / "tcp_coincidence_persistence_decision.csv"

DT = 0.01

# Timing: server is stepping continuously; we "wait" in wall-clock.
BASELINE_WAIT_S = 6.0

# Evidence ramp (best-effort):
RAMP_STEPS = 30                     # number of ramp ticks we attempt
RAMP_TICK_SLEEP_S = DT * 25         # mirror your old test cadence
RAMP_MAG_A = 0.020 * 1.03           # slight bias
RAMP_MAG_B = 0.020

# Coincidence pulse: short burst
PULSE_STEPS = 4
PULSE_SLEEP_S = DT * 25
STRIATUM_POKE_MAG = 1.0             # old reliable poke scale

# Value authorization
VALUE_REGION = "vta"                # or "snc"
VALUE_MAG = 0.78
VALUE_PULSE_ON_STEP = 1             # when to inject value within the pulse

# Post-decision observation
POST_STEPS = 80
POST_TICK_SLEEP_S = DT * 25

# ============================================================
# LOGGING
# ============================================================

def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log(line: str) -> None:
    msg = f"[{_ts()}] {line}"
    print(msg)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

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

def looks_unknown(out: str) -> bool:
    if not out:
        return True
    low = out.lower()
    return ("unknown command" in low) or ("unrecognized" in low) or ("error" in low and "traceback" not in low)

def first_working_cmd(candidates: List[str]) -> Optional[str]:
    """
    Return the first command (string) that the server seems to accept.
    We call it with dummy args when needed.
    """
    for c in candidates:
        out = send(c)
        if out and not looks_unknown(out):
            return c
    return None

# ============================================================
# PARSING (copied/compatible with your old test)
# ============================================================

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"

RE_CH_VAL = re.compile(rf"\b(D1|D2)\b\s*(?:=|:)\s*({_NUM})", re.I)
RE_WINNER_EQ = re.compile(r"^\s*winner\s*=\s*(\w+)\s*$", re.I)
RE_WINNER_COLON = re.compile(r"^\s*Winner\s*:\s*(\w+)\s*$", re.I)
RE_RELIEF = re.compile(rf"\brelief\s*=\s*({_NUM})", re.I)
RE_DECISION_FIELD = re.compile(r"\s*(\w+)\s*=\s*(.+)")
RE_CONTROL_JSONISH = re.compile(r'"phase"\s*:\s*"([^"]+)"', re.I)

def parse_striatum(out: str) -> Optional[Tuple[str, float, float]]:
    if not out:
        return None
    winner = ""
    d1 = None
    d2 = None
    for line in out.splitlines():
        ls = line.strip()
        m = RE_WINNER_EQ.match(ls)
        if m:
            winner = m.group(1).strip()
            continue
        m = RE_WINNER_COLON.match(ls)
        if m:
            winner = m.group(1).strip()
            continue
        m = RE_CH_VAL.search(ls)
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
        try:
            data[k] = float(v)
        except Exception:
            data[k] = v
    return data if data else None

def parse_control_phase(out: str) -> Optional[str]:
    """
    Your control output often contains a JSON-ish block.
    We only grab "phase" if present.
    """
    if not out:
        return None
    m = RE_CONTROL_JSONISH.search(out)
    return m.group(1) if m else None

# ============================================================
# CSV
# ============================================================

def init_csvs() -> None:
    with open(DEBUG_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step",
            "wall_t",
            "phase",
            "winner",
            "D1",
            "D2",
            "delta",
            "gate_relief",
            "decision_seen",
            "control_phase",
            "raw_striatum_len",
            "raw_gate_len",
            "raw_decision_len",
            "raw_control_len",
        ])

    with open(DECISION_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            "step",
            "wall_t",
            "winner",
            "delta_dominance",
            "relief",
            "time",
        ])

def append_debug(
    step: int,
    phase: str,
    winner: str,
    d1: float,
    d2: float,
    relief: Optional[float],
    decision_seen: bool,
    control_phase: Optional[str],
    raw_striatum: str,
    raw_gate: str,
    raw_decision: str,
    raw_control: str,
) -> None:
    with open(DEBUG_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            time.time(),
            phase,
            winner,
            d1,
            d2,
            abs(d1 - d2),
            "" if relief is None else relief,
            int(decision_seen),
            control_phase or "",
            len(raw_striatum or ""),
            len(raw_gate or ""),
            len(raw_decision or ""),
            len(raw_control or ""),
        ])

def append_decision(step: int, decision: Dict[str, Any]) -> None:
    with open(DECISION_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            step,
            time.time(),
            decision.get("winner"),
            decision.get("delta_dominance"),
            decision.get("relief"),
            decision.get("time"),
        ])

# ============================================================
# High-level actions
# ============================================================

def poke(region: str, mag: float) -> None:
    send(f"poke {region} {mag}", expect_reply=False)

def evidence_tick(best_effort_cmd: Optional[str], a_mag: float, b_mag: float) -> None:
    """
    Best-effort attempt to stimulate two competing assemblies (like your new test).
    If we can't, we degrade to region-level association cortex pokes.

    We try to use a discovered "stimulus-like" command if available.
    """
    if best_effort_cmd:
        # We attempt "assembly 0" and "assembly 1" styles via candidate formatting.
        # This is intentionally flexible because your command server naming might vary.
        tried = False
        for fmt in [
            f"{best_effort_cmd} association_cortex 0 {a_mag}",
            f"{best_effort_cmd} association_cortex 1 {b_mag}",
            f"{best_effort_cmd} association_cortex 0 {a_mag:.6f}",
            f"{best_effort_cmd} association_cortex 1 {b_mag:.6f}",
        ]:
            out = send(fmt)
            if out and not looks_unknown(out):
                tried = True

        if tried:
            return

    # Fallback: poke association cortex as a whole (less “honest”, but still upstream).
    poke("association_cortex", a_mag)
    poke("association_cortex", b_mag)

@dataclass
class Snapshot:
    winner: str = ""
    d1: float = 0.0
    d2: float = 0.0
    relief: Optional[float] = None
    decision: Optional[Dict[str, Any]] = None
    control_phase: Optional[str] = None
    raw_striatum: str = ""
    raw_gate: str = ""
    raw_decision: str = ""
    raw_control: str = ""

def snapshot(decision_only_until_seen: bool, decision_seen: bool) -> Snapshot:
    s = Snapshot()

    # Striatum dominance
    raw_str = send("striatum")
    parsed = parse_striatum(raw_str)
    if not parsed:
        raw_diag = send("striatum_diag")
        parsed = parse_striatum(raw_diag)
        if parsed:
            raw_str = raw_diag

    if parsed:
        s.winner, s.d1, s.d2 = parsed
    s.raw_striatum = raw_str

    # Gate relief
    raw_gate = send("gate")
    s.relief = parse_gate_relief(raw_gate)
    s.raw_gate = raw_gate

    # Control state (if available)
    raw_control = send("control")
    if raw_control and not looks_unknown(raw_control):
        s.control_phase = parse_control_phase(raw_control)
        s.raw_control = raw_control

    # Decision state (only query while not yet seen if asked)
    raw_decision = ""
    if (not decision_only_until_seen) or (not decision_seen):
        raw_decision = send("decision")
        dec = parse_decision(raw_decision)
        if dec:
            s.decision = dec
    s.raw_decision = raw_decision

    return s

# ============================================================
# MAIN
# ============================================================

def main() -> None:
    log("=== BEGIN TCP COINCIDENCE PERSISTENCE TEST ===")
    init_csvs()

    # Probe help & find a likely assembly stimulus command
    help_out = send("help")
    if help_out:
        log("[HELP] Retrieved help output (truncated):")
        log(help_out[:600])

    # Candidate names your server might have used historically.
    # We verify by actually calling them.
    stim_cmd = first_working_cmd([
        "stim",            # common
        "stimulus",        # explicit
        "inject",          # generic
        "pokeasm",         # made-up but plausible
        "poke_asm",        # plausible
        "poke_assembly",   # plausible
    ])
    if stim_cmd:
        log(f"[INFO] Found stimulus-like command: '{stim_cmd}'")
    else:
        log("[INFO] No stimulus-like command found; will fallback to region-level association pokes.")

    decision_seen = False
    step = 0

    # ------------------------------------------------------------
    # Phase 1: Baseline settle
    # ------------------------------------------------------------
    log("[PHASE 1] Baseline settle (no pokes)")
    time.sleep(BASELINE_WAIT_S)

    # ------------------------------------------------------------
    # Phase 2: Structural asymmetry / evidence ramp (best effort)
    # ------------------------------------------------------------
    log("[PHASE 2] Evidence ramp (best-effort association cortex targeting)")
    for i in range(RAMP_STEPS):
        evidence_tick(stim_cmd, RAMP_MAG_A, RAMP_MAG_B)
        time.sleep(RAMP_TICK_SLEEP_S)

        snap = snapshot(decision_only_until_seen=True, decision_seen=decision_seen)
        delta = abs(snap.d1 - snap.d2)
        if i % 5 == 0:
            log(f"[RAMP {i:04d}] Δ={delta:.6f} relief={(snap.relief if snap.relief is not None else -1):.4f}")

        append_debug(
            step=step,
            phase="ramp",
            winner=snap.winner,
            d1=snap.d1,
            d2=snap.d2,
            relief=snap.relief,
            decision_seen=decision_seen,
            control_phase=snap.control_phase,
            raw_striatum=snap.raw_striatum,
            raw_gate=snap.raw_gate,
            raw_decision=snap.raw_decision,
            raw_control=snap.raw_control,
        )
        step += 1

    # ------------------------------------------------------------
    # Phase 3: Coincidence pulse (striatal poke + temporary value)
    # ------------------------------------------------------------
    log("[PHASE 3] Coincidence pulse (striatal poke; temporary value authorization)")

    for j in range(1, PULSE_STEPS + 1):
        # "Lawful" enough under TCP constraints: we can't poke D1/D2 separately,
        # so we poke striatum uniformly (old machinery) and add value briefly.
        poke("striatum", STRIATUM_POKE_MAG)

        if j == VALUE_PULSE_ON_STEP:
            log(f"[VALUE] Injecting value via {VALUE_REGION} ({VALUE_MAG})")
            poke(VALUE_REGION, VALUE_MAG)

        time.sleep(PULSE_SLEEP_S)

        snap = snapshot(decision_only_until_seen=True, decision_seen=decision_seen)
        if snap.decision and not decision_seen:
            decision_seen = True
            append_decision(step, snap.decision)
            log(
                f"[DECISION] winner={snap.decision.get('winner')} "
                f"Δ={float(snap.decision.get('delta_dominance', 0.0)):.6f} "
                f"relief={float(snap.decision.get('relief', 0.0)):.4f} "
                f"t={float(snap.decision.get('time', 0.0)):.3f}"
            )

        append_debug(
            step=step,
            phase="pulse",
            winner=snap.winner,
            d1=snap.d1,
            d2=snap.d2,
            relief=snap.relief,
            decision_seen=decision_seen,
            control_phase=snap.control_phase,
            raw_striatum=snap.raw_striatum,
            raw_gate=snap.raw_gate,
            raw_decision=snap.raw_decision,
            raw_control=snap.raw_control,
        )
        step += 1

    # ------------------------------------------------------------
    # Phase 3½: Post-pulse check
    # ------------------------------------------------------------
    snap = snapshot(decision_only_until_seen=False, decision_seen=decision_seen)
    delta = abs(snap.d1 - snap.d2)
    log(f"[POST-PULSE] Δ={delta:.6f} relief={(snap.relief if snap.relief is not None else -1):.4f} decision={'YES' if snap.decision else 'NO'}")

    if not decision_seen and not snap.decision:
        log("!!! No decision fired — coincidence insufficient (acceptable). Ending test.")
        log(f"Outputs:\n  {DEBUG_CSV_PATH}\n  {DECISION_CSV_PATH}\n  {LOG_PATH}")
        return

    # If decision was only detected in this final snapshot:
    if snap.decision and not decision_seen:
        decision_seen = True
        append_decision(step, snap.decision)
        log(
            f"[DECISION] winner={snap.decision.get('winner')} "
            f"Δ={float(snap.decision.get('delta_dominance', 0.0)):.6f} "
            f"relief={float(snap.decision.get('relief', 0.0)):.4f} "
            f"t={float(snap.decision.get('time', 0.0)):.3f}"
        )

    # ------------------------------------------------------------
    # Phase 4: Post-decision persistence (NO STIMULUS)
    # ------------------------------------------------------------
    log("[PHASE 4] Post-decision persistence (no stimulus)")

    for i in range(POST_STEPS):
        time.sleep(POST_TICK_SLEEP_S)

        snap = snapshot(decision_only_until_seen=True, decision_seen=True)
        if i % 10 == 0:
            delta = abs(snap.d1 - snap.d2)
            log(f"[POST {i:04d}] Δ={delta:.6f} relief={(snap.relief if snap.relief is not None else -1):.4f} control_phase={snap.control_phase}")

        append_debug(
            step=step,
            phase="post",
            winner=snap.winner,
            d1=snap.d1,
            d2=snap.d2,
            relief=snap.relief,
            decision_seen=True,
            control_phase=snap.control_phase,
            raw_striatum=snap.raw_striatum,
            raw_gate=snap.raw_gate,
            raw_decision=snap.raw_decision,
            raw_control=snap.raw_control,
        )
        step += 1

    log("=== TEST COMPLETE ===")
    log("Expectations (observational-only):")
    log("• Decision may or may not fire (both acceptable).")
    log("• If it fires: no re-decision, control enters post-commit, persistence observable, then decay.")
    log("• No threshold hacks. No direct dominance injection (only pokes via server).")
    log(f"Outputs:\n  {DEBUG_CSV_PATH}\n  {DECISION_CSV_PATH}\n  {LOG_PATH}")

if __name__ == "__main__":
    main()
