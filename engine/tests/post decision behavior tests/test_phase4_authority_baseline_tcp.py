from __future__ import annotations

import csv
import json
import socket
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ============================================================
# PHASE 4 — AUTHORITY BASELINE (TCP)
#
# Purpose:
#   Build a "behavioral authority matrix" over time, using only TCP observables.
#
# What it does:
#   1) Optional clean-start (reset_latch, clear value/salience/hypotheses)
#   2) Baseline snapshots (pre-commit)
#   3) Lawful commit via "force_commit"
#   4) Observe post-commit -> decay -> release -> baseline return (no asserts)
#
# Requirements:
#   - test_runtime.py (or equivalent live runtime loop) must be running,
#     with command_server listening on HOST:PORT.
# ============================================================

# ------------------------------
# TCP CONFIG
# ------------------------------
HOST = "127.0.0.1"
PORT = 5557

# Runtime dt is informational here; we sleep against wall clock.
DT = 0.01
SLEEP_S = DT * 25  # matches your other TCP tests pacing

# Observation horizon
OBS_STEPS = 220
LOG_EVERY = 10

# Optional cleanup to reduce cross-run contamination
CLEAN_START = True

# ------------------------------
# OUTPUT PATHS
# ------------------------------
BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_DIR = BASE_DIR / "engine" / "tests" / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = time.strftime("%Y%m%d_%H%M%S")
LOG_PATH = OUT_DIR / f"tcp_phase4_authority_baseline_{STAMP}.txt"
CSV_PATH = OUT_DIR / f"tcp_phase4_authority_baseline_{STAMP}.csv"


# ============================================================
# TCP HELPERS
# ============================================================

def _send(cmd: str, timeout: float = 3.0) -> str:
    """
    One-shot TCP request. Returns response string (stripped).
    """
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
            sock.sendall((cmd.strip() + "\n").encode("utf-8"))
            data = sock.recv(65535)
            return data.decode("utf-8", errors="replace").strip()
    except Exception as e:
        _log(f"[TCP ERROR] cmd='{cmd}' err={e}")
        return ""


def _ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _log(msg: str) -> None:
    line = f"[{_ts()}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ============================================================
# PARSERS (best-effort; never hard-fail)
# ============================================================

def _parse_prefixed_json(block: str, prefix: str) -> Optional[Dict[str, Any]]:
    """
    Parses strings like:
      "CONTROL:\n{ ...json... }"
    """
    if not block:
        return None
    if not block.startswith(prefix):
        return None
    try:
        payload = block[len(prefix):].strip()
        return json.loads(payload)
    except Exception:
        return None


def _parse_kv_lines(block: str) -> Dict[str, str]:
    """
    Parses key=value pairs from lines like:
      DECISION:
        winner=D2
        delta_dominance=0.05
        relief=0.54
    """
    out: Dict[str, str] = {}
    if not block:
        return out
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.endswith(":"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _parse_gate_relief(gate_block: str) -> Optional[float]:
    """
    Parses:
      GATE:
        t=...
        relief=0.5456
        winner=D2
    """
    kv = _parse_kv_lines(gate_block)
    try:
        return float(kv.get("relief", ""))
    except Exception:
        return None


def _parse_value(value_block: str) -> Optional[float]:
    """
    Parses:
      VALUE: 0.6000
    """
    if not value_block:
        return None
    if not value_block.startswith("VALUE:"):
        return None
    try:
        return float(value_block.split(":", 1)[1].strip())
    except Exception:
        return None


def _parse_urgency(urg_block: str) -> Tuple[Optional[float], Optional[bool]]:
    """
    Parses:
      URGENCY:
        value=0.1234
        enabled=True
    """
    kv = _parse_kv_lines(urg_block)
    u = None
    en = None
    try:
        if "value" in kv:
            u = float(kv["value"])
    except Exception:
        pass
    try:
        if "enabled" in kv:
            en = kv["enabled"].lower() == "true"
    except Exception:
        pass
    return u, en


def _extract_control_fields(control_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Pulls canonical fields if present; keeps None if absent.
    """
    out: Dict[str, Any] = {
        "phase": None,
        "decision_made": None,
        "committed": None,
        "suppress_alternatives": None,
        "decision_winner": None,
        "fatigue_flag": None,
        "saturation_flag": None,
    }
    if not control_json:
        return out

    for k in list(out.keys()):
        if k in control_json:
            out[k] = control_json.get(k)
    return out


def _extract_working_fields(working_json: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Working snapshot is adapter-defined; we try common keys:
      active / engaged / working_state_active
      strength / value / gain
    """
    out: Dict[str, Any] = {
        "working_active": None,
        "working_strength": None,
        "working_gain": None,
    }
    if not working_json:
        return out

    # Active flag heuristics
    for key in ("working_state_active", "active", "engaged", "is_active"):
        if key in working_json and out["working_active"] is None:
            out["working_active"] = working_json.get(key)

    # Strength heuristics
    for key in ("strength", "working_strength", "value"):
        if key in working_json and out["working_strength"] is None:
            out["working_strength"] = working_json.get(key)

    # Gain heuristics
    for key in ("gain", "working_gain", "persistence_gain"):
        if key in working_json and out["working_gain"] is None:
            out["working_gain"] = working_json.get(key)

    return out


# ============================================================
# CSV
# ============================================================

CSV_HEADER = [
    "obs_idx",
    "wall_time",
    # control fields
    "phase",
    "decision_made",
    "committed",
    "suppress_alternatives",
    "decision_winner",
    "fatigue_flag",
    "saturation_flag",
    # working fields
    "working_active",
    "working_strength",
    "working_gain",
    # gate + decision
    "gate_relief",
    "decision_winner_raw",
    "decision_delta",
    "decision_relief",
    # value + urgency
    "value",
    "urgency",
    "urgency_enabled",
    # raw (truncated)
    "control_raw",
    "working_raw",
    "gate_raw",
    "decision_raw",
]


def _init_csv() -> None:
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(CSV_HEADER)


def _truncate(s: str, n: int = 400) -> str:
    s = s or ""
    s = s.replace("\n", "\\n")
    return s[:n]


def _append_csv(row: Dict[str, Any]) -> None:
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([row.get(col, "") for col in CSV_HEADER])


# ============================================================
# SNAPSHOT
# ============================================================

def snapshot() -> Dict[str, Any]:
    """
    Pulls a full authority snapshot (best-effort) using TCP-only commands.
    """
    control_raw = _send("control")
    working_raw = _send("working")
    gate_raw = _send("gate")
    decision_raw = _send("decision")
    value_raw = _send("value")
    urgency_raw = _send("urgency")

    control_json = _parse_prefixed_json(control_raw, "CONTROL:")
    working_json = _parse_prefixed_json(working_raw, "WORKING:")

    cf = _extract_control_fields(control_json)
    wf = _extract_working_fields(working_json)

    # gate relief
    gate_relief = _parse_gate_relief(gate_raw)

    # decision kvs
    dkv = _parse_kv_lines(decision_raw)
    d_winner = dkv.get("winner")
    d_delta = None
    d_relief = None
    try:
        if "delta_dominance" in dkv:
            d_delta = float(dkv["delta_dominance"])
        elif "delta" in dkv:
            d_delta = float(dkv["delta"])
    except Exception:
        pass
    try:
        if "relief" in dkv:
            d_relief = float(dkv["relief"])
    except Exception:
        pass

    # value
    v = _parse_value(value_raw)

    # urgency
    u, u_en = _parse_urgency(urgency_raw)

    return {
        **cf,
        **wf,
        "gate_relief": gate_relief,
        "decision_winner_raw": d_winner,
        "decision_delta": d_delta,
        "decision_relief": d_relief,
        "value": v,
        "urgency": u,
        "urgency_enabled": u_en,
        "control_raw": _truncate(control_raw),
        "working_raw": _truncate(working_raw),
        "gate_raw": _truncate(gate_raw),
        "decision_raw": _truncate(decision_raw),
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    _log("=== BEGIN PHASE 4 AUTHORITY BASELINE (TCP) ===")
    _init_csv()

    # --------------------------------------------------------
    # Optional clean-start (reduces cross-run contamination)
    # --------------------------------------------------------
    if CLEAN_START:
        _log("[CLEAN] reset_latch / clear value / clear salience / reset hypotheses")
        _send("reset_latch")
        _send("value_clear")
        _send("salience_clear")
        _send("hypothesis_reset")
        time.sleep(DT * 10)

    # --------------------------------------------------------
    # Phase 0: baseline snapshots
    # --------------------------------------------------------
    _log("[PHASE 0] Baseline snapshots (pre-commit)")
    base0 = snapshot()
    base0["obs_idx"] = -2
    base0["wall_time"] = time.time()
    _append_csv(base0)

    time.sleep(SLEEP_S)

    base1 = snapshot()
    base1["obs_idx"] = -1
    base1["wall_time"] = time.time()
    _append_csv(base1)

    _log(f"[BASELINE] phase={base1.get('phase')} committed={base1.get('committed')} "
         f"gate_relief={base1.get('gate_relief')} value={base1.get('value')} urgency={base1.get('urgency')}")

    # --------------------------------------------------------
    # Phase 1: lawful forced commit
    # --------------------------------------------------------
    _log("[PHASE 1] Force lawful commit (coincidence window only)")
    _send("force_commit")
    time.sleep(DT * 15)

    post = snapshot()
    post["obs_idx"] = 0
    post["wall_time"] = time.time()
    _append_csv(post)

    _log(f"[POST] phase={post.get('phase')} committed={post.get('committed')} "
         f"suppress={post.get('suppress_alternatives')} working_active={post.get('working_active')} "
         f"gate_relief={post.get('gate_relief')} decision={post.get('decision_winner_raw')}")

    # --------------------------------------------------------
    # Phase 2: observe authority over time
    # --------------------------------------------------------
    _log("[PHASE 2] Observing post-commit -> decay -> release (no asserts)")
    for i in range(1, OBS_STEPS + 1):
        time.sleep(SLEEP_S)
        row = snapshot()
        row["obs_idx"] = i
        row["wall_time"] = time.time()
        _append_csv(row)

        if i % LOG_EVERY == 0:
            _log(
                f"[OBS {i:04d}] phase={row.get('phase')} committed={row.get('committed')} "
                f"suppress={row.get('suppress_alternatives')} working={row.get('working_active')} "
                f"gate={row.get('gate_relief')} val={row.get('value')} urg={row.get('urgency')} "
                f"dec={row.get('decision_winner_raw')}"
            )

    _log("=== TEST COMPLETE ===")
    _log("This test is observational-only (no asserts).")
    _log("Use outputs to build the Phase-4 Authority Matrix:")
    _log("  - Which modulators remain live post-commit?")
    _log("  - Which should clamp/freeze during commitment?")
    _log("  - Do control/working flags unwind cleanly?")
    _log(f"Outputs:\n  {CSV_PATH}\n  {LOG_PATH}")


if __name__ == "__main__":
    main()
