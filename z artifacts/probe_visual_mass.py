from __future__ import annotations

import socket
import time
from typing import Dict, List

HOST = "127.0.0.1"
PORT = 5557

REGIONS = ["visual_input", "lgn", "v1", "pulvinar"]
POP_PROBES = [
    ("visual_input", "VISUAL_SIGNAL"),
    ("lgn", "RELAY_CELLS"),
]

SAMPLE_DT = 0.05          # seconds
TOTAL_TIME = 10.0         # seconds
OUT_FILE = "visual_mass_probe.csv"


def send(cmd: str) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(cmd.encode("utf-8"))
        return s.recv(4096).decode("utf-8").strip()


def parse_mass(line: str) -> float:
    # expects: REGION MASS=x MEAN=y STD=z N=n
    for part in line.split():
        if part.startswith("MASS="):
            return float(part.split("=")[1])
    return 0.0


def parse_pop_mass(line: str) -> float:
    # expects: region:pop MASS=x MEAN=y STD=z N=n
    for part in line.split():
        if part.startswith("MASS="):
            return float(part.split("=")[1])
    return 0.0


def main() -> None:
    print("[probe] connecting to runtime…")

    headers = ["t"]
    for r in REGIONS:
        headers.append(f"{r}_mass")
    for r, p in POP_PROBES:
        headers.append(f"{r}.{p}_mass")

    rows: List[str] = [",".join(headers)]

    t0 = time.time()
    last: Dict[str, float] = {}

    while True:
        t = time.time() - t0
        if t >= TOTAL_TIME:
            break

        row = [f"{t:.3f}"]

        # --- region mass ---
        for r in REGIONS:
            resp = send(f"stats {r}")
            mass = parse_mass(resp)
            row.append(f"{mass:.6f}")
            last[r] = mass

        # --- population mass ---
        for r, p in POP_PROBES:
            resp = send(f"stats_pop {r} {p}")
            mass = parse_pop_mass(resp)
            row.append(f"{mass:.6f}")
            last[f"{r}.{p}"] = mass

        rows.append(",".join(row))
        time.sleep(SAMPLE_DT)

    with open(OUT_FILE, "w") as f:
        f.write("\n".join(rows))

    print(f"[probe] done → {OUT_FILE}")


if __name__ == "__main__":
    main()
