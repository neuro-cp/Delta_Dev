from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple


# ------------------------------------------------------------
# Defaults (tune freely)
# ------------------------------------------------------------

DEFAULT_ACTIVE_THRESHOLD = 0.01
DEFAULT_TOP_K = 10


# ------------------------------------------------------------
# Helpers (pure; offline)
# ------------------------------------------------------------

def load_dump(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fraction_active(assemblies: List[Dict], *, threshold: float = DEFAULT_ACTIVE_THRESHOLD) -> float:
    if not assemblies:
        return 0.0
    active = sum(1 for a in assemblies if float(a.get("output", 0.0)) > threshold)
    return active / len(assemblies)


def total_mass(assemblies: List[Dict]) -> float:
    return float(sum(float(a.get("output", 0.0)) for a in assemblies))


def top_k_assemblies(
    assemblies: List[Dict],
    k: int,
) -> List[Tuple[str, float]]:
    rows = [
        (str(a.get("assembly_id")), float(a.get("output", 0.0)))
        for a in assemblies
        if float(a.get("output", 0.0)) > 0.0
    ]
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows[:k]


def tier_counts(assemblies: List[Dict]) -> Dict[str, int]:
    """
    Coarse tiering of outputs.
    These boundaries are inspection-only and may evolve during mechanics calibration.
    """
    tiers = {"high": 0, "mid": 0, "low": 0, "zero": 0}
    for a in assemblies:
        out = float(a.get("output", 0.0))
        if out > 0.2:
            tiers["high"] += 1
        elif out > 0.05:
            tiers["mid"] += 1
        elif out > 0.0:
            tiers["low"] += 1
        else:
            tiers["zero"] += 1
    return tiers


def overlap_fraction(
    top_a: List[Tuple[str, float]],
    top_b: List[Tuple[str, float]],
) -> float:
    if not top_a:
        return 0.0
    ids_a = {aid for aid, _ in top_a}
    ids_b = {aid for aid, _ in top_b}
    return len(ids_a & ids_b) / len(ids_a)


# ------------------------------------------------------------
# Convenience CLI for ad-hoc inspection
# ------------------------------------------------------------

def analyze_pair(baseline_path: Path, post_path: Path, *, top_k: int = DEFAULT_TOP_K, threshold: float = DEFAULT_ACTIVE_THRESHOLD) -> None:
    base = load_dump(baseline_path)
    post = load_dump(post_path)

    base_asm = base["assemblies"]
    post_asm = post["assemblies"]

    print("=" * 80)
    print(f"REGION: {base.get('region')}")
    print(f"BASELINE STEP: {base.get('step')}")
    print(f"POST STEP: {post.get('step')}")
    print("=" * 80)

    base_mass = total_mass(base_asm)
    base_frac = fraction_active(base_asm, threshold=threshold)
    base_top = top_k_assemblies(base_asm, top_k)
    base_tiers = tier_counts(base_asm)

    print("\n[BASELINE]")
    print(f"Total mass:       {base_mass:.6f}")
    print(f"Fraction active:  {base_frac:.4f}")
    print(f"Tiers:            {base_tiers}")
    print("Top assemblies:")
    for aid, val in base_top:
        print(f"  {aid:<60} {val:.6f}")

    post_mass = total_mass(post_asm)
    post_frac = fraction_active(post_asm, threshold=threshold)
    post_top = top_k_assemblies(post_asm, top_k)
    post_tiers = tier_counts(post_asm)

    print("\n[POST]")
    print(f"Total mass:       {post_mass:.6f}")
    print(f"Fraction active:  {post_frac:.4f}")
    print(f"Tiers:            {post_tiers}")
    print("Top assemblies:")
    for aid, val in post_top:
        print(f"  {aid:<60} {val:.6f}")

    overlap = overlap_fraction(base_top, post_top)

    print("\n[RECRUITMENT SUMMARY]")
    print(f"Δ mass:           {post_mass - base_mass:.6f}")
    print(f"Δ fraction:       {post_frac - base_frac:.4f}")
    print(f"Top-K overlap:    {overlap:.4f}")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python recruitment_stats_from_dump.py <baseline.json> <post.json>")
        sys.exit(1)

    analyze_pair(Path(sys.argv[1]), Path(sys.argv[2]))
