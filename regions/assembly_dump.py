from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime


ROOT = Path(__file__).resolve().parent
OUT_FILE = ROOT / "assembly_dump.txt"


def main():
    # --------------------------------------------------
    # Load + compile brain (definitions only)
    # --------------------------------------------------
    loader = NeuralFrameworkLoader(ROOT)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    # --------------------------------------------------
    # Instantiate runtime (assemblies created here)
    # --------------------------------------------------
    runtime = BrainRuntime(brain, dt=0.01)

    # --------------------------------------------------
    # Dump assemblies (structure only)
    # --------------------------------------------------
    lines = []
    lines.append("ASSEMBLY DUMP\n")
    lines.append("=" * 80 + "\n")

    for rid, region in runtime.region_states.items():
        pops = region.get("populations", {}) or {}
        for pop_name, plist in pops.items():
            for p in plist:
                lines.append(
                    f"{p.assembly_id}\n"
                    f"  region       : {rid}\n"
                    f"  population   : {pop_name}\n"
                    f"  size         : {p.size}\n"
                    f"  baseline     : {p.baseline:.6f}\n"
                    "\n"
                )

    OUT_FILE.write_text("".join(lines))
    print(f"[OK] Assembly dump written to {OUT_FILE}")


if __name__ == "__main__":
    main()
