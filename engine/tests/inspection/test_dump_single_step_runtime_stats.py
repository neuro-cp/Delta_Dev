from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _basic_stats(values: List[float]):
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return mean, var ** 0.5


def region_stats(runtime: BrainRuntime, region_id: str) -> Dict[str, float]:
    region = runtime.region_states.get(region_id)
    if not region:
        return {}

    acts: List[float] = []
    outs: List[float] = []

    for plist in region.get("populations", {}).values():
        for pop in plist:
            acts.append(float(getattr(pop, "activity", 0.0)))
            outs.append(float(pop.output()))

    mean, std = _basic_stats(acts)

    return {
        "mass": float(sum(outs)),
        "mean": float(mean),
        "std": float(std),
        "n": float(len(acts)),
    }


# ------------------------------------------------------------
# Test
# ------------------------------------------------------------

def test_dump_single_step_runtime_stats(tmp_path: Path) -> None:
    """
    Build runtime, step once, poke once, step N times,
    dump assembly + region stats to a txt file.
    """

    # -------------------------
    # Load + compile
    # -------------------------

    repo_root = Path(__file__).resolve().parents[3]

    loader = NeuralFrameworkLoader(repo_root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain, dt=0.01)

    # -------------------------
    # Baseline step
    # -------------------------

    runtime.step()

    # -------------------------
    # Apply poke (change region if desired)
    # -------------------------

    target_region = "v1"
    poke_magnitude = 0.2

    runtime.inject_stimulus(target_region, magnitude=poke_magnitude)

    # -------------------------
    # Step forward
    # -------------------------

    steps_after_poke = 50
    for _ in range(steps_after_poke):
        runtime.step()

    # -------------------------
    # Dump stats
    # -------------------------

    out_path = repo_root / "single_step_runtime_dump.txt"

    with out_path.open("w", encoding="utf-8") as f:
        f.write("=== REGION STATS ===\n")
        for rid in sorted(runtime.region_states.keys()):
            s = region_stats(runtime, rid)
            if not s:
                continue
            f.write(
                f"{rid:20} "
                f"MASS={s['mass']:.6f} "
                f"MEAN={s['mean']:.6f} "
                f"STD={s['std']:.6f} "
                f"N={int(s['n'])}\n"
            )

        f.write("\n=== ASSEMBLY STATS ===\n")
        f.write(
            f"{'ASSEMBLY_ID':55} {'REGION':20} {'ACTIVITY':>10} {'OUTPUT':>10}\n"
        )

        for pop in runtime._all_pops:
            aid = getattr(pop, "assembly_id", "")
            if not aid:
                continue
            rid = getattr(pop, "region_id", "")
            act = float(getattr(pop, "activity", 0.0))
            out = float(pop.output())

            f.write(
                f"{aid:55} {rid:20} {act:10.6f} {out:10.6f}\n"
            )

    # Make the artifact visible to pytest output
    print(f"\n[DUMP WRITTEN] {out_path}")
