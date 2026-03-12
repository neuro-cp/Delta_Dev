import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import math


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

    if start_pos is None and len(data) > 0:

        first = data[0]["state"]

        start_pos = tuple(first["agent_position"])

        if first.get("targets"):
            target_pos = tuple(first["targets"][0])

        if first.get("hazards"):
            hazard_positions = [tuple(h) for h in first["hazards"]]

    for step in data:

        x, y = step["state"]["agent_position"]

        if 0 <= x <= GRID_MAX and 0 <= y <= GRID_MAX:
            heat[y, x] += 1


# --------------------------------------------------
# COMPUTE NAVIGATION VECTOR FIELD
# --------------------------------------------------

field_x = np.zeros_like(heat)
field_y = np.zeros_like(heat)

if target_pos:

    tx, ty = target_pos

    for y in range(GRID_MAX + 1):
        for x in range(GRID_MAX + 1):

            dx = tx - x
            dy = ty - y

            dist = abs(dx) + abs(dy)

            denom = max(dist, 1)

            dir_x = dx / denom
            dir_y = dy / denom

            # directional halo (same as encoder)
            direction_gain = 1.0 + 1.2 * math.exp(-1.2 * dist)

            gx = dir_x * direction_gain
            gy = dir_y * direction_gain

            # hazard repulsion
            rx = 0
            ry = 0

            for hx, hy in hazard_positions:

                dxh = x - hx
                dyh = y - hy

                hdist = abs(dxh) + abs(dyh)

                if hdist == 0:
                    continue

                repulsion = (
                    1.3 * math.exp(-1.4 * hdist)
                    + 0.8 / (hdist + 1)
                )

                rx += (dxh / hdist) * repulsion
                ry += (dyh / hdist) * repulsion

            field_x[y, x] = gx + rx
            field_y[y, x] = gy + ry


# --------------------------------------------------
# PLOT HEATMAP + VECTOR FIELD
# --------------------------------------------------

plt.figure(figsize=(7,7))

plt.imshow(heat, origin="lower", cmap="hot", alpha=0.75)
plt.colorbar(label="visit frequency")

X, Y = np.meshgrid(range(GRID_MAX + 1), range(GRID_MAX + 1))

plt.quiver(
    X,
    Y,
    field_x,
    field_y,
    color="white",
    angles="xy",
    scale_units="xy",
    scale=1
)

plt.title("Trajectory Density + Navigation Field")
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