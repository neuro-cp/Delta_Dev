from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ------------------------------------------------------------
# Config
# ------------------------------------------------------------

DT = 0.01
BASELINE_SECONDS = 1.0
POKE_SECONDS = 3.0
POKE_REGION = "stn"
POKE_MAGNITUDE = 125.0
TOP_K = 10

OUT_FILE = "poke_response_fingerprint.txt"


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def top_k_assemblies(
    runtime: BrainRuntime,
    region: str,
    k: int,
) -> List[Tuple[str, float]]:
    rows = []
    region_state = runtime.region_states.get(region)
    if not region_state:
        return rows

    for plist in region_state.get("populations", {}).values():
        for pop in plist:
            out = float(pop.output())
            if out > 0.0:
                rows.append((pop.assembly_id, out))

    rows.sort(key=lambda x: x[1], reverse=True)
    return rows[:k]


def fraction_active(runtime: BrainRuntime, region: str) -> float:
    region_state = runtime.region_states.get(region)
    if not region_state:
        return 0.0

    total = 0
    active = 0

    for plist in region_state.get("populations", {}).values():
        for pop in plist:
            total += 1
            if pop.output() > 0.0:
                active += 1

    return active / total if total else 0.0


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

def test_poke_response_fingerprint(tmp_path: Path) -> None:
    """
    Mechanical inspection test.

    Baseline (1s) → GPi poke → 3s response → dump fingerprint.
    """

    # --------------------------------------------------
    # Resolve repo root (same pattern as test_runtime.py)
    # --------------------------------------------------

    repo_root = Path(__file__).resolve().parents[3]

    # -------------------------
    # Load + compile
    # -------------------------

    loader = NeuralFrameworkLoader(repo_root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain, dt=DT)

    baseline_steps = int(BASELINE_SECONDS / DT)
    poke_steps = int(POKE_SECONDS / DT)

    out_path = repo_root / OUT_FILE

    with out_path.open("w", encoding="utf-8") as f:
        f.write("POKE RESPONSE FINGERPRINT\n")
        f.write("=" * 80 + "\n\n")

        # -------------------------
        # Baseline
        # -------------------------

        for _ in range(baseline_steps):
            runtime.step()

        baseline_stats = runtime.snapshot_region_stats(POKE_REGION)
        baseline_mass = baseline_stats["mass"]

        baseline_frac = fraction_active(runtime, POKE_REGION)
        baseline_top = top_k_assemblies(runtime, POKE_REGION, TOP_K)

        f.write("[BASELINE]\n")
        f.write(f"Region: {POKE_REGION}\n")
        f.write(f"Mass: {baseline_mass:.6f}\n")
        f.write(f"Fraction active: {baseline_frac:.4f}\n")
        f.write("Top assemblies:\n")
        for aid, val in baseline_top:
            f.write(f"  {aid:<60} {val:.6f}\n")
        f.write("\n")

        # -------------------------
        # Poke
        # -------------------------

        runtime.inject_stimulus(POKE_REGION, magnitude=POKE_MAGNITUDE)

        for _ in range(poke_steps):
            runtime.step()

        poke_stats = runtime.snapshot_region_stats(POKE_REGION)
        poke_mass = poke_stats["mass"]

        poke_frac = fraction_active(runtime, POKE_REGION)
        poke_top = top_k_assemblies(runtime, POKE_REGION, TOP_K)

        f.write("[POST-POKE]\n")
        f.write(f"Region: {POKE_REGION}\n")
        f.write(f"Poke magnitude: {POKE_MAGNITUDE}\n")
        f.write(f"Mass: {poke_mass:.6f}\n")
        f.write(f"Fraction active: {poke_frac:.4f}\n")
        f.write("Top assemblies:\n")
        for aid, val in poke_top:
            f.write(f"  {aid:<60} {val:.6f}\n")

    assert out_path.exists()
    assert out_path.stat().st_size > 0
