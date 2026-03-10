import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

EPISODE_DIR = Path(r"C:\Users\Admin\Desktop\delta\episodes\3-1v2")

# grid bounds (increase if environment expands)
GRID_MAX = 10


# --------------------------------------------------
# LOAD TRAJECTORIES
# --------------------------------------------------

heat = np.zeros((GRID_MAX + 1, GRID_MAX + 1))

episode_files = sorted(EPISODE_DIR.glob("episode_*/episode_trace.json"))

start_pos = None
target_pos = None
hazard_pos = None

for ep in episode_files:

    with open(ep) as f:
        data = json.load(f)

    # extract environment metadata from first step
    if start_pos is None:
        first = data[0]["state"]

        start_pos = tuple(first["agent_position"])

        if first["targets"]:
            target_pos = tuple(first["targets"][0])

        if first["hazards"]:
            hazard_pos = tuple(first["hazards"][0])

    # accumulate trajectory visits
    for step in data:

        x, y = step["state"]["agent_position"]

        if 0 <= x <= GRID_MAX and 0 <= y <= GRID_MAX:
            heat[y, x] += 1


# --------------------------------------------------
# PLOT HEATMAP
# --------------------------------------------------

plt.figure(figsize=(6, 6))

plt.imshow(heat, origin="lower", cmap="hot")

plt.colorbar(label="visit frequency")

plt.title("Agent Trajectory Density")
plt.xlabel("X")
plt.ylabel("Y")


# --------------------------------------------------
# MARK ENVIRONMENT FEATURES
# --------------------------------------------------

if start_pos:
    plt.scatter([start_pos[0]], [start_pos[1]],
                marker="o", label=f"start {start_pos}")

if target_pos:
    plt.scatter([target_pos[0]], [target_pos[1]],
                marker="*", label=f"target {target_pos}")

if hazard_pos:
    plt.scatter([hazard_pos[0]], [hazard_pos[1]],
                marker="x", label=f"hazard {hazard_pos}")

plt.legend()

plt.show()