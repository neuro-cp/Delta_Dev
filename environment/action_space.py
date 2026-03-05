from enum import Enum


class ActionType(Enum):
    """
    Legal action space for the environment.

    Candidate strategies will eventually choose among these.
    """

    MOVE_NORTH = "move_north"
    MOVE_SOUTH = "move_south"
    MOVE_EAST = "move_east"
    MOVE_WEST = "move_west"

    SCAN = "scan"

    ENGAGE = "engage"

    WAIT = "wait"


ALL_ACTIONS = [
    ActionType.MOVE_NORTH,
    ActionType.MOVE_SOUTH,
    ActionType.MOVE_EAST,
    ActionType.MOVE_WEST,
    ActionType.SCAN,
    ActionType.ENGAGE,
    ActionType.WAIT,
]