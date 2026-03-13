from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class WorldState:
    """
    Minimal world state representation.

    This object represents the full environment snapshot at a given timestep.
    It is immutable in practice: transitions should clone and modify.
    """

    agent_position: Tuple[int, int]

    resources: int

    targets: List[Tuple[int, int]]

    hazards: List[Tuple[int, int]]

    time_step: int = 0

    def clone(self):
        """
        Create a safe copy of the state for simulation stepping.
        """
        return WorldState(
            agent_position=self.agent_position,
            resources=self.resources,
            targets=list(self.targets),
            hazards=list(self.hazards),
            time_step=self.time_step,
        )

    def is_terminal(self) -> bool:
        """
        Determines whether an episode should end.
        """
        if self.resources <= 0:
            return True

        if len(self.targets) == 0:
            return True

        return False
