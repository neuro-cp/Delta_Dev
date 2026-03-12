import json
from pathlib import Path

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BASELINE_DIR = Path(r"C:\Users\Admin\Desktop\delta\episodes\Baseline_episodes")
V1_DIR = Path(r"C:\Users\Admin\Desktop\delta\episodes\barrier_eps2")

HAZARD_POS = (2,2)


# --------------------------------------------------
# CORE ANALYSIS
# --------------------------------------------------

def analyze_directory(directory):

    total_landings = 0
    total_steps = 0
    episode_count = 0

    for ep in sorted(directory.glob("episode_*/episode_trace.json")):

        episode_count += 1

        with open(ep) as f:
            data = json.load(f)

        for step in data:

            pos = tuple(step["state"]["agent_position"])

            if pos == HAZARD_POS:
                total_landings += 1

            total_steps += 1

    return {
        "episodes": episode_count,
        "total_steps": total_steps,
        "hazard_landings": total_landings,
        "landings_per_episode": total_landings / episode_count if episode_count else 0,
        "landing_rate": total_landings / total_steps if total_steps else 0
    }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    baseline = analyze_directory(BASELINE_DIR)
    v1 = analyze_directory(V1_DIR)

    print("\nBASELINE RESULTS")
    print("----------------")
    for k, v in baseline.items():
        print(f"{k}: {v}")

    print("\n RESULTS")
    print("----------")
    for k, v in v1.items():
        print(f"{k}: {v}")

    print("\nCOMPARISON")
    print("----------")
    print(
        "hazard change factor:",
        v1["hazard_landings"] / baseline["hazard_landings"]
        if baseline["hazard_landings"] else "undefined"
    )


if __name__ == "__main__":
    main()