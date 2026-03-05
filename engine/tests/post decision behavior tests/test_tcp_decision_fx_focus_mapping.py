from __future__ import annotations

import csv
import json
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List


# ============================================================
# CONFIG
# ============================================================

HOST = "127.0.0.1"
PORT = 5557

DT = 0.20
POST_COMMIT_SAMPLES = 30

OUT_DIR = Path(__file__).resolve().parent / "_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Try these until we find a JSON payload that contains region_gain
FX_DUMP_COMMANDS = [
    "decision_fx",
    "fx",
    "effects",
    "decisionfx",
    "decisionfx_dump",
]


# ============================================================
# TCP helpers
# ============================================================

def _recv_all(sock: socket.socket, *, max_seconds: float = 0.6) -> str:
    """
    Read whatever the server sends for a short window.
    The command server is usually 'one response per command'.
    """
    sock.settimeout(0.2)
    chunks: List[bytes] = []
    t0 = time.time()
    while time.time() - t0 < max_seconds:
        try:
            data = sock.recv(4096)
            if not data:
                break
            chunks.append(data)
            # If response ends with newline and nothing else arrives quickly, we're done.
            if data.endswith(b"\n"):
                # give it one tiny chance to send more
                time.sleep(0.03)
        except socket.timeout:
            break
    return b"".join(chunks).decode("utf-8", errors="replace")


def send_cmd(cmd: str) -> str:
    """
    Send one command to the running test_runtime TCP server.
    """
    with socket.create_connection((HOST, PORT), timeout=2.0) as sock:
        sock.sendall((cmd.strip() + "\n").encode("utf-8"))
        return _recv_all(sock)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort extraction of a JSON object embedded in a response.
    Many of your dumps are pretty-printed JSON.
    """
    i = text.find("{")
    j = text.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return None
    blob = text[i : j + 1]
    try:
        return json.loads(blob)
    except Exception:
        return None


# ============================================================
# Domain helpers
# ============================================================

@dataclass
class FxSnapshot:
    thalamic_gain: float
    region_gain: Dict[str, float]
    suppress_channels: Dict[str, float]
    lock_action: bool


def fetch_fx_snapshot() -> Tuple[Optional[FxSnapshot], str, str]:
    """
    Try multiple commands until we get a JSON payload containing region_gain.
    Returns: (snapshot_or_none, used_command, raw_text)
    """
    last_raw = ""
    for cmd in FX_DUMP_COMMANDS:
        raw = send_cmd(cmd)
        last_raw = raw
        payload = _extract_json(raw)
        if not payload:
            continue
        if "region_gain" in payload:
            try:
                snap = FxSnapshot(
                    thalamic_gain=float(payload.get("thalamic_gain", 1.0)),
                    region_gain=dict(payload.get("region_gain", {}) or {}),
                    suppress_channels=dict(payload.get("suppress_channels", {}) or {}),
                    lock_action=bool(payload.get("lock_action", False)),
                )
                return snap, cmd, raw
            except Exception:
                continue
    return None, "<none>", last_raw


def fetch_decision_state() -> Tuple[Optional[Dict[str, Any]], str]:
    raw = send_cmd("decision")
    payload = _extract_json(raw)
    return payload, raw


def fetch_control_state() -> Tuple[Optional[Dict[str, Any]], str]:
    raw = send_cmd("control")
    payload = _extract_json(raw)
    return payload, raw


def force_commit_best_effort() -> str:
    """
    Your server has a test-only force_commit. Syntax may vary by build, so we try a few.
    """
    candidates = [
        "force_commit",
        "force_commit 4",
        "force_commit 5",
        "force_commit sustain=5",
    ]
    raw_all = []
    for c in candidates:
        raw = send_cmd(c)
        raw_all.append(f"$ {c}\n{raw}")
        # Very loose success heuristic
        if "OK" in raw or "commit" in raw.lower() or "DECISION" in raw:
            return "\n".join(raw_all)
    return "\n".join(raw_all)


# ============================================================
# Test
# ============================================================

def main() -> None:
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_txt = OUT_DIR / f"tcp_decision_fx_focus_mapping_{ts}.txt"
    out_csv = OUT_DIR / f"tcp_decision_fx_focus_mapping_{ts}.csv"

    def log(line: str) -> None:
        print(line)
        with out_txt.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === BEGIN: Decision FX Focus Mapping Audit ===")
    log(f"[target] {HOST}:{PORT}")
    log("[CLEAN] reset_latch + value_clear")
    log(send_cmd("reset_latch").strip() or "(no response)")
    log(send_cmd("value_clear").strip() or "(no response)")

    # Give the runtime one beat to incorporate the resets (cheap insurance).
    time.sleep(0.25)

    # Confirm server understands 'decision' / 'control'
    d0, d0raw = fetch_decision_state()
    c0, c0raw = fetch_control_state()
    log("[probe] decision:")
    log(d0raw.strip())
    log("[probe] control:")
    log(c0raw.strip())

    log("[ACTION] force_commit (best-effort)")
    log(force_commit_best_effort())

    # Sample a short window post-commit and inspect FX routing output
    log(f"[PHASE] post_commit sampling x{POST_COMMIT_SAMPLES} @ dt={DT:.2f}s")

    with out_csv.open("w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv)
        w.writerow([
            "i",
            "winner",
            "commit",
            "confidence",
            "fx_cmd",
            "thalamic_gain",
            "lock_action",
            "region_gain_keys",
            "winner_key_present_as_region",
            "pfc_gain",
        ])

        for i in range(POST_COMMIT_SAMPLES):
            d, _ = fetch_decision_state()
            winner = None
            commit = False
            conf = 0.0
            if isinstance(d, dict):
                winner = d.get("winner")
                commit = bool(d.get("commit", False))
                conf = float(d.get("confidence", 0.0) or 0.0)

            fx, fx_cmd, fx_raw = fetch_fx_snapshot()
            th_gain = 1.0
            lock_action = False
            region_keys = []
            winner_key_present = False
            pfc_gain = 1.0

            if fx:
                th_gain = fx.thalamic_gain
                lock_action = fx.lock_action
                region_keys = sorted(list(fx.region_gain.keys()))
                winner_key_present = (winner is not None and winner in fx.region_gain)
                # most-likely initial focus region
                if "pfc" in fx.region_gain:
                    pfc_gain = float(fx.region_gain["pfc"])

            log(f"[{i:04d}] commit={commit} winner={winner} conf={conf:.3f} "
                f"fx_cmd={fx_cmd} lock={lock_action} th_gain={th_gain:.3f} "
                f"region_keys={region_keys}")

            w.writerow([
                i,
                winner,
                commit,
                f"{conf:.6f}",
                fx_cmd,
                f"{th_gain:.6f}",
                int(lock_action),
                "|".join(region_keys),
                int(winner_key_present),
                f"{pfc_gain:.6f}",
            ])

            time.sleep(DT)

    # Verdict: observational + clear hints
    fx_last, fx_cmd_last, _ = fetch_fx_snapshot()
    d_last, _ = fetch_decision_state()
    winner_last = d_last.get("winner") if isinstance(d_last, dict) else None

    log("=== VERDICT ===")
    if not fx_last:
        log("FAIL-ish: Could not retrieve a JSON FX snapshot containing region_gain.")
        log("  - Your server might not expose decision_fx yet, or the command name differs.")
        log("  - Run 'help' in your TCP console and add the real FX dump command to FX_DUMP_COMMANDS.")
    else:
        region_keys = sorted(list(fx_last.region_gain.keys()))
        bad_key = (winner_last is not None and winner_last in fx_last.region_gain)
        good_key = ("pfc" in fx_last.region_gain) or (len(region_keys) > 0 and not bad_key)

        log(f"FX dump command used: {fx_cmd_last}")
        log(f"Winner: {winner_last}")
        log(f"region_gain keys: {region_keys}")

        if bad_key:
            log("FAIL: region_gain still keyed by winner label (D1/D2). Mapping not applied or not used.")
        elif good_key:
            log("PASS: region_gain appears keyed by real region(s), not D1/D2. Focus mapping is alive.")
        else:
            log("INCONCLUSIVE: FX snapshot exists but region_gain is empty. That can be ok in low-confidence mode.")

    log("=== END ===")
    log(f"Outputs:\n  {out_txt}\n  {out_csv}")


if __name__ == "__main__":
    main()
