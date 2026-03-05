import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt


GRID_SIZE = 10


def load_episode(path):
    with open(path) as f:
        return json.load(f)


def draw_state(ax, state):

    ax.clear()

    agent_x, agent_y = state["agent_position"]

    targets = state["targets"]
    hazards = state["hazards"]

    # draw grid
    ax.set_xlim(-1, GRID_SIZE)
    ax.set_ylim(-1, GRID_SIZE)
    ax.set_xticks(range(GRID_SIZE))
    ax.set_yticks(range(GRID_SIZE))
    ax.grid(True)

    # draw targets
    for tx, ty in targets:
        ax.scatter(tx, ty, s=200, marker="*", color="green")

    # draw hazards
    for hx, hy in hazards:
        ax.scatter(hx, hy, s=200, marker="X", color="red")

    # draw agent
    ax.scatter(agent_x, agent_y, s=200, marker="o", color="blue")

    ax.set_title(f"Agent: ({agent_x},{agent_y})")


def play_episode(trace):

    fig, ax = plt.subplots()

    for step in trace:

        state = step["state"]

        draw_state(ax, state)

        plt.pause(0.2)

    plt.show()


def main():

    if len(sys.argv) < 2:
        print("usage: python visualize_episode.py episode_trace.json")
        return

    path = Path(sys.argv[1])

    trace = load_episode(path)

    play_episode(trace)


if __name__ == "__main__":
    main()