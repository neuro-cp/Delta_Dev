import json
import sys
from pathlib import Path


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def load_episode(ep_dir: Path):
    trace_file = ep_dir / "episode_trace.json"

    if not trace_file.exists():
        raise FileNotFoundError(f"No episode_trace.json in {ep_dir}")

    with open(trace_file) as f:
        return json.load(f)


def analyze(trace):

    positions = []
    actions = []
    distances = []
    reversals = 0

    for step in trace:

        pos = tuple(step["state"]["agent_position"])
        positions.append(pos)

        action = step["action"]
        actions.append(action)

        dist = step["metrics"].get("distance_to_target")
        if dist is not None:
            distances.append(dist)

        if step["metrics"].get("reversal"):
            reversals += 1

    steps = len(trace)

    # exploration radius
    origin = positions[0]
    radii = [manhattan(origin, p) for p in positions]
    max_radius = max(radii)

    # distance trend
    distance_slope = None
    if len(distances) >= 2:
        distance_slope = distances[-1] - distances[0]

    # unique cells visited
    unique_cells = len(set(positions))

    # reversal rate
    reversal_rate = reversals / steps if steps else 0

    report = {
        "steps": steps,
        "unique_cells_visited": unique_cells,
        "exploration_radius": max_radius,
        "reversal_rate": reversal_rate,
        "distance_start": distances[0] if distances else None,
        "distance_end": distances[-1] if distances else None,
        "distance_slope": distance_slope,
    }

    return report


def write_report(ep_dir: Path, report):

    json_out = ep_dir / "trajectory_analysis.json"
    txt_out = ep_dir / "trajectory_analysis.txt"

    with open(json_out, "w") as f:
        json.dump(report, f, indent=2)

    with open(txt_out, "w") as f:

        f.write("Trajectory Analysis\n")
        f.write("==================\n\n")

        for k, v in report.items():
            f.write(f"{k}: {v}\n")


def main():

    if len(sys.argv) < 2:
        print("usage: python trajectory_analyzer.py <episode_dir>")
        return

    ep_dir = Path(sys.argv[1])

    trace = load_episode(ep_dir)

    report = analyze(trace)

    write_report(ep_dir, report)

    print("analysis written to:")
    print(ep_dir / "trajectory_analysis.json")
    print(ep_dir / "trajectory_analysis.txt")


if __name__ == "__main__":
    main()