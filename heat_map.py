import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

EPISODE_DIR = Path(r"C:\Users\Admin\Desktop\delta\episodes\episodes_barrier_test")
GRID_MAX = 10


# --------------------------------------------------
# LOAD TRAJECTORIES
# --------------------------------------------------

heat = np.zeros((GRID_MAX + 1, GRID_MAX + 1))

episode_files = sorted(EPISODE_DIR.glob("episode_*/episode_trace.json"))

start_pos = None
target_pos = None
hazard_positions = []

for ep in episode_files:

    with open(ep) as f:
        data = json.load(f)

    # read environment metadata once
    if start_pos is None and len(data) > 0:

        first = data[0]["state"]

        start_pos = tuple(first["agent_position"])

        if first.get("targets"):
            target_pos = tuple(first["targets"][0])

        if first.get("hazards"):
            hazard_positions = [tuple(h) for h in first["hazards"]]

    # accumulate trajectory density
    for step in data:

        x, y = step["state"]["agent_position"]

        if 0 <= x <= GRID_MAX and 0 <= y <= GRID_MAX:
            heat[y, x] += 1


# --------------------------------------------------
# PLOT HEATMAP
# --------------------------------------------------

plt.figure(figsize=(6,6))

plt.imshow(heat, origin="lower", cmap="hot")
plt.colorbar(label="visit frequency")

plt.title("Agent Trajectory Density")
plt.xlabel("X")
plt.ylabel("Y")


# --------------------------------------------------
# MARK ENVIRONMENT FEATURES
# --------------------------------------------------

if start_pos:
    plt.scatter(
        start_pos[0],
        start_pos[1],
        marker="o",
        color="blue",
        s=120,
        label=f"start {start_pos}"
    )

if target_pos:
    plt.scatter(
        target_pos[0],
        target_pos[1],
        marker="*",
        color="lime",
        s=200,
        label=f"target {target_pos}"
    )

if hazard_positions:

    hx = [h[0] for h in hazard_positions]
    hy = [h[1] for h in hazard_positions]

    plt.scatter(
        hx,
        hy,
        marker="x",
        color="cyan",
        s=100,
        label="hazards"
    )

plt.legend()
plt.show()