import math
import random

from environment.action_space import ActionType


class PolicyMatrix:
    """
    Converts directional field information into
    a probability distribution over actions.

    Design principles
    -----------------
    - movement is always dominant
    - exploration occurs through directional randomness
    - SCAN/WAIT remain extremely rare
    """

    MOVE_WEIGHT = 1.0
    EXPLORE_GAIN = 0.55

    # SCAN / WAIT kept minimal
    SCAN_WEIGHT = 0.02
    WAIT_WEIGHT = 0.01

    def compute(self, dir_x, dir_y):

        magnitude = math.sqrt(dir_x * dir_x + dir_y * dir_y)

        # exploration increases as field weakens
        explore = (1.0 - min(magnitude, 1.0)) * 1.0 * self.EXPLORE_GAIN

        # directional bias
        north = max(dir_y, 0.0) * self.MOVE_WEIGHT
        south = max(-dir_y, 0.0) * self.MOVE_WEIGHT
        east = max(dir_x, 0.0) * self.MOVE_WEIGHT
        west = max(-dir_x, 0.0) * self.MOVE_WEIGHT

        # exploration adds motion noise
        north += explore
        south += explore
        east += explore
        west += explore

        weights = {
            ActionType.MOVE_NORTH: north,
            ActionType.MOVE_SOUTH: south,
            ActionType.MOVE_EAST: east,
            ActionType.MOVE_WEST: west,
            ActionType.SCAN: self.SCAN_WEIGHT,
            ActionType.WAIT: self.WAIT_WEIGHT,
            ActionType.ENGAGE: 0.0,
        }

        total = sum(weights.values())

        if total <= 0.0:
            # fallback: always move randomly
            return {
                ActionType.MOVE_NORTH: 0.25,
                ActionType.MOVE_SOUTH: 0.25,
                ActionType.MOVE_EAST: 0.25,
                ActionType.MOVE_WEST: 0.25,
                ActionType.SCAN: 0.0,
                ActionType.WAIT: 0.0,
                ActionType.ENGAGE: 0.0,
            }

        for action in weights:
            weights[action] /= total

        return weights


def sample_action(weights):

    r = random.random()
    cumulative = 0.0

    for action, prob in weights.items():
        cumulative += prob
        if r <= cumulative:
            return action

    return list(weights.keys())[-1]