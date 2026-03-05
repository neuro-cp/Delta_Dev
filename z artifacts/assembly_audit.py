# audit_assemblies.py
# One-shot assembly census for the neural framework
# READ-ONLY: no dynamics, no stepping, no mutation

from pathlib import Path
from collections import defaultdict

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


# ============================================================
# CONFIG
# ============================================================

ROOT = Path("C:/Users/Admin/Desktop/neural framework")
DT = 0.01


# ============================================================
# LOAD BRAIN (STRUCTURE ONLY)
# ============================================================

loader = NeuralFrameworkLoader(ROOT)
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
# ASSEMBLY CENSUS
# ============================================================

rows = []

for region_id, region in runtime.region_states.items():
    assembly_count = 0
    pop_count = 0

    for plist in region["populations"].values():
        pop_count += len(plist)
        assembly_count += len(plist)

    rows.append({
        "region": region_id,
        "assemblies": assembly_count,
        "populations": len(region["populations"]),
        "population_instances": pop_count,
    })

# sort by assembly count (ascending = danger at top)
rows.sort(key=lambda r: r["assemblies"])


# ============================================================
# PRINT REPORT
# ============================================================

print("\n=== ASSEMBLY AUDIT REPORT ===")
print(f"{'REGION':20} {'ASSEMBLIES':>10} {'POPS':>6} {'INST':>6}")
print("-" * 50)

for r in rows:
    flag = ""
    if r["assemblies"] == 0 and r["populations"] > 0:
        flag = "  <-- ERROR: 0 assemblies"
    elif r["assemblies"] == 1:
        flag = "  <-- WARN: singleton"

    print(
        f"{r['region']:20} "
        f"{r['assemblies']:10d} "
        f"{r['populations']:6d} "
        f"{r['population_instances']:6d}"
        f"{flag}"
    )

print("-" * 50)

# ============================================================
# SUMMARY CHECKS
# ============================================================

zero_regions = [r["region"] for r in rows if r["assemblies"] == 0 and r["populations"] > 0]
singleton_regions = [r["region"] for r in rows if r["assemblies"] == 1]

print("\nSUMMARY:")
print(f"  Regions with 0 assemblies (ERROR): {len(zero_regions)}")
for r in zero_regions:
    print(f"    - {r}")

print(f"\n  Regions with 1 assembly (WARN): {len(singleton_regions)}")
for r in singleton_regions:
    print(f"    - {r}")

print("\nAudit complete.")
