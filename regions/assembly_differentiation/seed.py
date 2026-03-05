from __future__ import annotations

import hashlib

# ============================================================
# changing this will destroy all assembly characteristics
# ============================================================

SEED_PHRASE = "OHANA MEANS FAMILY!"

def get_seed_int(bits: int = 32) -> int:
    
    if bits not in (32, 64):
        raise ValueError("bits must be 32 or 64")

    digest = hashlib.sha256(SEED_PHRASE.encode("utf-8")).digest()

    if bits == 32:
        return int.from_bytes(digest[:4], byteorder="big", signed=False)

    return int.from_bytes(digest[:8], byteorder="big", signed=False)


def get_seed_hex() -> str:
    """
    fingerprint for logs and dumps.
    """
    return hashlib.sha256(SEED_PHRASE.encode("utf-8")).hexdigest()[:12]
