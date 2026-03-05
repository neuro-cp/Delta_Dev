import socket
import time
from typing import Iterable, Optional


# ----------------------------
# CONFIG
# ----------------------------

HOST = "127.0.0.1"
PORT = 5557

# Choose one:
# - "stress": big values to see if anything explodes
# - "semantic": smaller values to observe gating/propagation
MODE = "semantic"

if MODE == "stress":
    POKE_VALUES = [20, 100, 500, 2500, 10000]
else:
    POKE_VALUES = [1, 2, 5, 10, 20, 50]

DELAY_SECONDS = 5.0

REGIONS = [
    "lgn", "md", "mgb", "pulvinar", "trn", "vpl", "vpm",
    "v1", "a1", "s1", "association_cortex", "pfc",
    "striatum", "gpe", "gpi", "stn", "snc", "vta",
    "locus_coeruleus", "raphe",
    "inferior_colliculus", "superior_colliculus",
    "ca1", "ca3", "dentate_gyrus", "subiculum",
    "hypothalamus", "anterior_pituitary", "posterior_pituitary",
    "cerebellar_cortex", "deep_nuclei",
    "autonomic_system",
]

# If True, request a quick stat line after each poke
AFTER_POKE_STATS = False


# ----------------------------
# TCP SESSION
# ----------------------------

class CommandClient:
    def __init__(self, host: str, port: int, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None

    def __enter__(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.sock:
                self.sock.close()
        finally:
            self.sock = None

    def send(self, cmd: str) -> str:
        if not self.sock:
            raise RuntimeError("Socket not connected")
        self.sock.sendall((cmd.strip() + "\n").encode("utf-8"))
        try:
            data = self.sock.recv(4096)
            return data.decode("utf-8", errors="replace").strip()
        except Exception:
            return ""


# ----------------------------
# MAIN
# ----------------------------

print("=== BEGIN LOG-SCALE REGION POKE SWEEP ===")
print(f"mode = {MODE}")
print(f"poke values = {POKE_VALUES}, delay = {DELAY_SECONDS}s")
print(f"regions = {len(REGIONS)}")
print("-" * 80)

with CommandClient(HOST, PORT, timeout=5.0) as client:
    for poke_value in POKE_VALUES:
        print(f"\n--- BEGIN POKE STRENGTH: {poke_value} ---")

        for region in REGIONS:
            cmd = f"poke {region} {poke_value}"
            try:
                rep = client.send(cmd)
                print(f"[SENT] {cmd} :: {rep or 'OK'}")

                if AFTER_POKE_STATS:
                    stats = client.send(f"stats {region}")
                    if stats:
                        print(f"[STATS] {stats}")

            except Exception as e:
                print(f"[ERROR] {cmd} -> {e}")

            time.sleep(DELAY_SECONDS)

        print(f"--- END POKE STRENGTH: {poke_value} ---")

print("\n=== ALL POKES COMPLETE ===")
