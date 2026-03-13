import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import math


# --------------------------------------------------
# CONFIG
# --------------------------------------------------

EPISODE_DIR = Path(r"C:\Users\Admin\Desktop\delta\episodes\episodes_barrier_test")
PADDING = 2


# --------------------------------------------------
# LOAD TRAJECTORIES
# --------------------------------------------------

episode_files = sorted(EPISODE_DIR.glob("episode_*/episode_trace.json"))

trajectory_points = []
start_pos = None
target_pos = None
hazard_positions = []


for ep in episode_files:

    with open(ep) as f:
        data = json.load(f)

    if not data:
        continue

    if start_pos is None:

        first = data[0]["state"]

        start_pos = tuple(first["agent_position"])

        if first.get("targets"):
            target_pos = tuple(first["targets"][0])

        if first.get("hazards"):
            hazard_positions = [tuple(h) for h in first["hazards"]]

    for step in data:

        x, y = step["state"]["agent_position"]
        trajectory_points.append((x, y))


# --------------------------------------------------
# DETERMINE DYNAMIC BOUNDS
# --------------------------------------------------

xs = [p[0] for p in trajectory_points]
ys = [p[1] for p in trajectory_points]

if target_pos:
    xs.append(target_pos[0])
    ys.append(target_pos[1])

for hx, hy in hazard_positions:
    xs.append(hx)
    ys.append(hy)

xmin = min(xs) - PADDING
xmax = max(xs) + PADDING
ymin = min(ys) - PADDING
ymax = max(ys) + PADDING


width = xmax - xmin + 1
height = ymax - ymin + 1


# --------------------------------------------------
# BUILD HEATMAP
# --------------------------------------------------

heat = np.zeros((height, width))

for x, y in trajectory_points:

    gx = x - xmin
    gy = y - ymin

    heat[gy, gx] += 1


# --------------------------------------------------
# COMPUTE NAVIGATION VECTOR FIELD
# --------------------------------------------------

field_x = np.zeros_like(heat)
field_y = np.zeros_like(heat)

if target_pos:

    tx, ty = target_pos

    for gy in range(height):
        for gx in range(width):

            x = gx + xmin
            y = gy + ymin

            dx = tx - x
            dy = ty - y

            dist = abs(dx) + abs(dy)

            denom = max(dist, 1)

            dir_x = dx / denom
            dir_y = dy / denom

            # target halo attraction
            direction_gain = 1.0 + 1.2 * math.exp(-1.2 * dist)

            gx_field = dir_x * direction_gain
            gy_field = dir_y * direction_gain

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

            field_x[gy, gx] = gx_field + rx
            field_y[gy, gx] = gy_field + ry


# --------------------------------------------------
# PLOT HEATMAP + VECTOR FIELD
# --------------------------------------------------

plt.figure(figsize=(8, 8))

extent = [xmin, xmax, ymin, ymax]

plt.imshow(
    heat,
    origin="lower",
    cmap="hot",
    alpha=0.75,
    extent=extent
)

plt.colorbar(label="visit frequency")


X, Y = np.meshgrid(
    np.arange(xmin, xmax + 1),
    np.arange(ymin, ymax + 1)
)

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