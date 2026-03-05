from typing import Tuple

from .world_state import WorldState
from .action_space import ActionType


class EnvironmentSimulator:
    """
    Applies an action to the world state and returns the resulting state.

    This layer is purely mechanical:
    - no learning
    - no cognition
    - no neural mutation
    """

    # --------------------------------------------------
    # WORLD GEOMETRY
    # --------------------------------------------------

    GRID_MIN = 0
    GRID_MAX = 20

    # --------------------------------------------------
    # STEP TRANSITION
    # --------------------------------------------------

    def step(self, state: WorldState, action: ActionType) -> Tuple[WorldState, dict]:

        new_state = state.clone()

        x, y = new_state.agent_position

        # --------------------------------------------------
        # MOVEMENT
        # --------------------------------------------------

        if action == ActionType.MOVE_NORTH:
            y += 1

        elif action == ActionType.MOVE_SOUTH:
            y -= 1

        elif action == ActionType.MOVE_EAST:
            x += 1

        elif action == ActionType.MOVE_WEST:
            x -= 1

        # --------------------------------------------------
        # CLAMP TO GRID BOUNDS
        # --------------------------------------------------

        x = max(self.GRID_MIN, min(x, self.GRID_MAX))
        y = max(self.GRID_MIN, min(y, self.GRID_MAX))

        new_state.agent_position = (x, y)

        # --------------------------------------------------
        # SCAN (placeholder)
        # --------------------------------------------------

        if action == ActionType.SCAN:
            pass

        # --------------------------------------------------
        # ENGAGE TARGET
        # --------------------------------------------------

        elif action == ActionType.ENGAGE:

            if new_state.targets:

                tx, ty = new_state.targets[0]
                ax, ay = new_state.agent_position

                dist = abs(tx - ax) + abs(ty - ay)

                # must be adjacent
                if dist <= 1:
                    new_state.targets.pop(0)

        # --------------------------------------------------
        # WAIT
        # --------------------------------------------------

        elif action == ActionType.WAIT:
            pass

        # --------------------------------------------------
        # RESOURCE COST
        # --------------------------------------------------

        new_state.resources = max(new_state.resources - 1, 0)

        # --------------------------------------------------
        # ADVANCE TIME
        # --------------------------------------------------

        new_state.time_step += 1

        metrics = self.evaluate(state, new_state)

        return new_state, metrics

    # --------------------------------------------------
    # TRANSITION METRICS
    # --------------------------------------------------

    def evaluate(self, previous: WorldState, new: WorldState) -> dict:
        """
        Computes diagnostic metrics describing the transition.
        """

        target_distance = None

        if new.targets:

            tx, ty = new.targets[0]
            ax, ay = new.agent_position

            # Manhattan distance
            target_distance = abs(tx - ax) + abs(ty - ay)

        metrics = {
            "targets_remaining": len(new.targets),
            "resource_delta": previous.resources - new.resources,
            "time": new.time_step,
            "agent_position": new.agent_position,
            "distance_to_target": target_distance,
        }

        return metrics