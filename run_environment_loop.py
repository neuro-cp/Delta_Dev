import json
from pathlib import Path

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

from environment.world_state import WorldState
from engine.loop.environment_runtime_loop import EnvironmentRuntimeLoop


# --------------------------------------------------
# PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent

EPISODE_DIR = ROOT / "episodes"
EPISODE_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# RUNTIME CONSTRUCTION
# --------------------------------------------------

def build_runtime():

    loader = NeuralFrameworkLoader(ROOT)

    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()

    brain = loader.compile(
        expression_profile="human_default",
        state_profile="awake",
        compound_profile="experimental",
    )

    runtime = BrainRuntime(brain, dt=0.01)

    return runtime


# --------------------------------------------------
# HOMEOSTATIC STABILIZATION
# --------------------------------------------------

def wait_for_homeostasis(runtime, region="pfc", decline_required=5, max_steps=10000):

    print("\nBOOTSTRAP: waiting for neural stabilization")

    prev_mass = None
    peak_mass = None
    decline_steps = 0

    for step in range(max_steps):

        runtime.step()

        stats = runtime.snapshot_region_stats(region)
        mass = stats["mass"]

        if prev_mass is not None:

            if peak_mass is None or mass > peak_mass:
                peak_mass = mass
                decline_steps = 0

            if mass < peak_mass:
                decline_steps += 1
            else:
                decline_steps = 0

            if decline_steps >= decline_required:
                print(f"HOMEOSTASIS DETECTED at step {step}")
                print(f"peak_mass = {peak_mass:.6f}")
                print(f"current_mass = {mass:.6f}")
                return

        prev_mass = mass

    print("WARNING: stabilization not detected within max_steps")


# --------------------------------------------------
# EPISODE STORAGE
# --------------------------------------------------

def next_episode_path():

    existing = sorted(EPISODE_DIR.glob("episode_*"))

    if not existing:
        idx = 1
    else:
        last = int(existing[-1].name.split("_")[1])
        idx = last + 1

    ep_path = EPISODE_DIR / f"episode_{idx:04d}"
    ep_path.mkdir()

    return ep_path


def save_episode(ep_path, episode_data):

    out = ep_path / "episode_trace.json"

    serializable = []

    for step in episode_data:

        serializable.append({
            "state": {
                "agent_position": step["state"].agent_position,
                "resources": step["state"].resources,
                "targets": step["state"].targets,
                "hazards": step["state"].hazards,
                "time_step": step["state"].time_step,
            },
            "action": str(step["action"]),
            "metrics": step["metrics"],
        })

    with open(out, "w") as f:
        json.dump(serializable, f, indent=2)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    runtime = build_runtime()

    # -----------------------------------------------
    # WAIT FOR NEURAL STABILIZATION
    # -----------------------------------------------

    wait_for_homeostasis(runtime)

    print("\nStarting environment episodes until success...")

    success = False
    episode_count = 0

    while not success:

        episode_count += 1
        print(f"\nRunning episode {episode_count}")

        ep_path = next_episode_path()

        loop = EnvironmentRuntimeLoop(runtime, episode_dir=ep_path)

        initial_state = WorldState(
            agent_position=(0, 0),
            resources=200,
            targets=[(5, 5)],
            hazards=[(2, 2)],
        )

        episode = loop.run_episode(initial_state)

        save_episode(ep_path, episode)

        last_metrics = episode[-1]["metrics"]

        if last_metrics["targets_remaining"] == 0:
            success = True
            print("\nSUCCESS: target reached")

        print("episode steps:", len(episode))
        print("saved to:", ep_path)

    print("\nMISSION COMPLETE")


if __name__ == "__main__":
    main()