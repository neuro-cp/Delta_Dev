from __future__ import annotations

import json
import socket
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# ============================================================
# TEST: TCP Value Control Surface
#
# Goal:
#   Determine which control surface actually drives the VALUE subsystem:
#     A) "poke vta <mag>"  (region stimulus)
#     B) "value_set <x>"   (subsystem interface)
#
# We log and print:
#   - VALUE (from "value")
#   - gate relief (from "gate")
#   - decision (from "decision")
#   - control snapshot (from "control") (step/time/phase/committed)
#
# This is observational-only: no asserts.
#
# REQUIREMENT:
#   Start your live runtime loop + command_server first.
#   (e.g., python test_runtime.py)
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

SLEEP_S = 0.20  # short pause between actions/snapshots

BASE_DIR = Path(r"C:\Users\Admin\Desktop\neural framework")
OUT_DIR = BASE_DIR / "engine" / "tests" / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STAMP = time.strftime("%Y%m%d_%H%M%S")
OUT_TXT = OUT_DIR / f"tcp_value_control_surface_{STAMP}.txt"


# ------------------------------
# TCP
# ------------------------------

def send(cmd: str, timeout: float = 3.0) -> str:
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as sock:
            sock.sendall((cmd.strip() + "\n").encode("utf-8"))
            data = sock.recv(65535)
            return data.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR: tcp failed for '{cmd}' -> {e}"


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(OUT_TXT, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ------------------------------
# Parsing helpers
# ------------------------------

def parse_value(s: str) -> Optional[float]:
    # expects "VALUE: 0.6000"
    if not s or not s.startswith("VALUE:"):
        return None
    try:
        return float(s.split(":", 1)[1].strip())
    except Exception:
        return None


def parse_kv_lines(block: str) -> Dict[str, str]:
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


def parse_gate_relief(gate_block: str) -> Optional[float]:
    kv = parse_kv_lines(gate_block)
    try:
        return float(kv.get("relief", ""))
    except Exception:
        return None


def parse_prefixed_json(block: str, prefix: str) -> Optional[Dict[str, Any]]:
    if not block or not block.startswith(prefix):
        return None
    try:
        payload = block[len(prefix):].strip()
        return json.loads(payload)
    except Exception:
        return None


def snapshot(tag: str) -> Dict[str, Any]:
    value_raw = send("value")
    gate_raw = send("gate")
    decision_raw = send("decision")
    control_raw = send("control")

    v = parse_value(value_raw)
    gate_relief = parse_gate_relief(gate_raw)
    dkv = parse_kv_lines(decision_raw)

    control_json = parse_prefixed_json(control_raw, "CONTROL:")
    phase = None
    committed = None
    step = None
    t = None
    if control_json:
        phase = control_json.get("phase")
        committed = control_json.get("committed")
        step = control_json.get("step")
        t = control_json.get("time")

    snap = {
        "tag": tag,
        "value_raw": value_raw,
        "value": v,
        "gate_relief": gate_relief,
        "decision_winner": dkv.get("winner"),
        "decision_delta": dkv.get("delta_dominance") or dkv.get("delta"),
        "decision_relief": dkv.get("relief"),
        "phase": phase,
        "committed": committed,
        "step": step,
        "time": t,
    }

    log(
        f"[{tag}] value={snap['value']} gate_relief={snap['gate_relief']} "
        f"dec={snap['decision_winner']} phase={snap['phase']} committed={snap['committed']} "
        f"(step={snap['step']} t={snap['time']})"
    )
    return snap


def main() -> None:
    log("=== BEGIN: TCP Value Control Surface Test ===")
    log(f"Target: {HOST}:{PORT}")
    log("Quick sanity: requesting help")
    help_txt = send("help")
    log("HELP (first 10 lines):")
    for line in help_txt.splitlines()[:10]:
        log("  " + line)

    # Clean start (avoid contamination)
    log("[CLEAN] reset_latch + value_clear")
    log("  " + send("reset_latch"))
    log("  " + send("value_clear"))
    time.sleep(SLEEP_S)

    s0 = snapshot("baseline_0")
    time.sleep(SLEEP_S)

    # --------------------------------------------------------
    # A) poke vta
    # --------------------------------------------------------
    target_value = 0.78
    log(f"[A] poke vta {target_value}")
    r = send(f"poke vta {target_value}")
    log("  " + r)
    time.sleep(SLEEP_S)

    sA1 = snapshot("after_poke_vta_1")
    time.sleep(SLEEP_S)

    sA2 = snapshot("after_poke_vta_2")
    time.sleep(SLEEP_S)

    # --------------------------------------------------------
    # B) value_set
    # --------------------------------------------------------
    log(f"[B] value_set {target_value}")
    r = send(f"value_set {target_value}")
    log("  " + r)
    time.sleep(SLEEP_S)

    sB1 = snapshot("after_value_set_1")
    time.sleep(SLEEP_S)

    sB2 = snapshot("after_value_set_2")
    time.sleep(SLEEP_S)

    # --------------------------------------------------------
    # Clear value
    # --------------------------------------------------------
    log("[CLEAN] value_clear")
    log("  " + send("value_clear"))
    time.sleep(SLEEP_S)

    sC = snapshot("after_value_clear")

    # --------------------------------------------------------
    # Interpretation (printed, not asserted)
    # --------------------------------------------------------
    def delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return b - a

    dv_poke = delta(s0["value"], sA1["value"])
    dv_set = delta(s0["value"], sB1["value"])
    log("=== SUMMARY ===")
    log(f"baseline value: {s0['value']}")
    log(f"Δvalue after poke vta: {dv_poke}")
    log(f"Δvalue after value_set: {dv_set}")
    log("Interpretation guide:")
    log("  - If poke vta does NOT change VALUE but value_set DOES: your older tests were using the wrong control surface.")
    log("  - If both change VALUE: both interfaces matter (and we need to decide which is canonical).")
    log("  - If neither changes VALUE: value subsystem may be disabled/unwired in the running runtime instance.")
    log(f"Output log: {OUT_TXT}")
    log("=== END ===")


if __name__ == "__main__":
    main()
