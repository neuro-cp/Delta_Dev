# test_runtime.py
# Deterministic persistence validation harness
# Validates BG persistence traces WITHOUT assuming semantic channels yet

from __future__ import annotations

from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ============================================================
# CONFIG
# ============================================================

DT = 0.01

PHASE_A_STEPS = 100     # seed persistence
PHASE_B_STEPS = 100     # symmetric stimulation
PHASE_C_STEPS = 300     # decay

POKE_MAG = 1.0

TARGET_REGION = "striatum"
TARGET_POP_PREFERRED = "D1_MSN"   # may or may not exist depending on region JSON

ASSEMBLY_A = 0
ASSEMBLY_B = 1


# ============================================================
# LOAD BRAIN
# ============================================================

root = Path(r"C:\Users\Admin\Desktop\neural framework")

loader = NeuralFrameworkLoader(root)
loader.load_neuron_bases()
loader.load_regions()
loader.load_profiles()

brain = loader.compile(
    expression_profile="human_default",
    state_profile="awake",
    compound_profile="experimental",
)

runtime = BrainRuntime(brain, dt=DT)


# ============================================================
# TARGET DISCOVERY (ROBUST)
# ============================================================

def resolve_target_population() -> str:
    reg = runtime.region_states.get(TARGET_REGION)
    if not reg:
        raise RuntimeError(f"Missing region '{TARGET_REGION}' in runtime.region_states")

    pops = reg.get("populations", {})
    if not pops:
        raise RuntimeError(f"Region '{TARGET_REGION}' has no populations")

    # Prefer explicit target if present
    if TARGET_POP_PREFERRED in pops and len(pops[TARGET_POP_PREFERRED]) >= 2:
        return TARGET_POP_PREFERRED

    # Otherwise pick the first population with at least 2 assemblies
    for pop_id, plist in pops.items():
        if len(plist) >= 2:
            return pop_id

    # Last resort: pick any population (we will validate indices)
    return next(iter(pops.keys()))


TARGET_POP = resolve_target_population()


def aid(idx: int) -> str:
    return f"{TARGET_REGION}:{TARGET_POP}:{idx}"


def validate_assemblies_exist() -> None:
    reg = runtime.region_states[TARGET_REGION]
    pops = reg["populations"]
    plist = pops.get(TARGET_POP, [])
    if not plist:
        raise RuntimeError(f"Target population '{TARGET_POP}' not found in '{TARGET_REGION}'")

    if max(ASSEMBLY_A, ASSEMBLY_B) >= len(plist):
        raise RuntimeError(
            f"Need assemblies {ASSEMBLY_A} and {ASSEMBLY_B} in {TARGET_REGION}:{TARGET_POP}, "
            f"but only have {len(plist)} assemblies"
        )


validate_assemblies_exist()

print("\n=== PERSISTENCE VALIDATION TEST ===")
print(f"Target population: {TARGET_REGION}:{TARGET_POP}")
print(f"Target assemblies: {aid(ASSEMBLY_A)} vs {aid(ASSEMBLY_B)}")
print("-" * 80)


# ============================================================
# HELPERS
# ============================================================

def poke(idx: int) -> None:
    runtime.inject_stimulus(
        region_id=TARGET_REGION,
        population_id=TARGET_POP,
        assembly_index=idx,
        magnitude=POKE_MAG,
    )


def trace_value(idx: int) -> float:
    trace = runtime.bg_persistence.traces.get(aid(idx))
    return float(trace.value) if trace else 0.0


def winner_label() -> str:
    """
    We do NOT assume semantic channel meaning here.
    We only report what the kernel last claimed as 'winner', if any.
    """
    k = runtime.competition_kernel

    # Newer kernel tends to expose winner by channel; fall back gracefully.
    w = getattr(k, "last_winner_channel", None)
    if w is not None:
        return str(w)

    w2 = getattr(k, "last_winner_id", None)
    if w2:
        return str(w2)

    return "none"


# ============================================================
# PHASE A — SEED PERSISTENCE
# ============================================================

print("\n[PHASE A] Seeding persistence (poke A only)")

for step in range(PHASE_A_STEPS):
    poke(ASSEMBLY_A)
    runtime.step()

    if step % 20 == 0:
        print(
            f"t={runtime.time:5.2f}s | "
            f"winner={winner_label():>12} | "
            f"trace(A)={trace_value(ASSEMBLY_A):.4f} | "
            f"trace(B)={trace_value(ASSEMBLY_B):.4f}"
        )


# ============================================================
# PHASE B — SYMMETRIC INPUT
# ============================================================

print("\n[PHASE B] Symmetric stimulation (A vs B)")

wins: dict[str, int] = {}

for step in range(PHASE_B_STEPS):
    poke(ASSEMBLY_A)
    poke(ASSEMBLY_B)
    runtime.step()

    w = winner_label()
    wins[w] = wins.get(w, 0) + 1

    if step % 20 == 0:
        print(
            f"t={runtime.time:5.2f}s | "
            f"winner={w:>12} | "
            f"trace(A)={trace_value(ASSEMBLY_A):.4f} | "
            f"trace(B)={trace_value(ASSEMBLY_B):.4f}"
        )

print("\n[PHASE B RESULT]")
print("Wins:", wins)


# ============================================================
# PHASE C — DECAY
# ============================================================

print("\n[PHASE C] Decay (no input)")

for step in range(PHASE_C_STEPS):
    runtime.step()

    if step % 50 == 0:
        print(
            f"t={runtime.time:5.2f}s | "
            f"trace(A)={trace_value(ASSEMBLY_A):.4f} | "
            f"trace(B)={trace_value(ASSEMBLY_B):.4f}"
        )


# ============================================================
# SUMMARY
# ============================================================

print("\n=== TEST COMPLETE ===")
print("Correct expectations at THIS stage:")
print("- Phase A: trace(A) rises, trace(B) ≈ 0")
print("- Phase B: winner may be unstable / 'none' / or a channel label")
print("- Phase C: traces decay smoothly toward 0")
print("=" * 80)
