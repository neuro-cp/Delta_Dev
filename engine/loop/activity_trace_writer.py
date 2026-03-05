import json
from pathlib import Path


class ActivityTraceWriter:
    """
    Maintains and saves the neural activity trace
    for a single episode.
    """

    def __init__(self):
        self.trace = []

    def append(self, step_record: dict):

        self.trace.append(step_record)

    def reset(self):

        self.trace = []

    def save(self, episode_dir: Path):

        output_path = episode_dir / "activity_trace.json"

        with open(output_path, "w") as f:
            json.dump(self.trace, f, indent=2)