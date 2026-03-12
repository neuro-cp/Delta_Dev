import json
from pathlib import Path


EPISODE_DIR = Path(r"C:\Users\Admin\Desktop\delta\episodes\barrier_eps2")


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def analyze_episode(ep_dir):

    trace_file = ep_dir / "episode_trace.json"

    if not trace_file.exists():
        print("Skipping:", ep_dir.name)
        return None

    with open(trace_file) as f:
        trace = json.load(f)

    distances = []

    for record in trace:

        state = record["state"]

        pos = tuple(state["agent_position"])
        target = tuple(state["targets"][0])

        d = manhattan(pos, target)
        distances.append(d)

    return {
        "episode": ep_dir.name,
        "steps": len(distances),
        "start_distance": distances[0],
        "end_distance": distances[-1],
        "avg_distance": sum(distances) / len(distances)
    }


def main():

    episodes = sorted(
        d for d in EPISODE_DIR.iterdir()
        if d.is_dir() and d.name.startswith("episode_")
    )

    results = []

    for ep in episodes:

        r = analyze_episode(ep)

        if r:
            results.append(r)

    if not results:
        print("No valid episodes found.")
        return

    print("\nEPISODE DISTANCE ANALYSIS")
    print("-------------------------")

    for r in results:
        print(
            f"{r['episode']} | "
            f"steps={r['steps']} | "
            f"start={r['start_distance']} | "
            f"end={r['end_distance']} | "
            f"avg={r['avg_distance']:.2f}"
        )

    avg_all = sum(r["avg_distance"] for r in results) / len(results)

    print("\nAverage distance across episodes:", round(avg_all, 2))


if __name__ == "__main__":
    main()