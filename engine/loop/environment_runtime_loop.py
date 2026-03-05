from environment.world_state import WorldState
from environment.simulator import EnvironmentSimulator
from environment.stimulus_encoder import StimulusEncoder
from environment.action_space import ALL_ACTIONS, ActionType

from engine.loop.step_activity_collector import StepActivityCollector
from engine.loop.activity_trace_writer import ActivityTraceWriter

import random
from pathlib import Path


class EnvironmentRuntimeLoop:
    """
    Orchestrates interaction between the neural substrate
    and the external environment.

    world state
        ↓
    stimulus encoding
        ↓
    runtime dynamics
        ↓
    action selection
        ↓
    environment transition
    """

    def __init__(self, runtime, episode_dir: Path | None = None):

        self.runtime = runtime

        self.simulator = EnvironmentSimulator()
        self.encoder = StimulusEncoder()

        # neural instrumentation
        self.activity_collector = StepActivityCollector(runtime)
        self.activity_writer = ActivityTraceWriter()

        self.episode_dir = episode_dir

        # diagnostics
        self.previous_action: ActionType | None = None

    def run_episode(self, initial_state: WorldState):

        state = initial_state
        episode_history = []

        step_index = 0

        # reset neural trace for new episode
        self.activity_writer.reset()

        # reset action diagnostics
        self.previous_action = None

        while not state.is_terminal():

            # --------------------------------------------------
            # 1. Encode world state into neural stimulation
            # --------------------------------------------------

            self.encoder.encode(state, self.runtime)

            # --------------------------------------------------
            # 2. Step neural runtime
            # --------------------------------------------------

            self.runtime.step()

            # --------------------------------------------------
            # 3. Select action
            # --------------------------------------------------

            action = self.select_action()

            # --------------------------------------------------
            # 4. Oscillation / reversal detection
            # --------------------------------------------------

            reversal = self._detect_reversal(action)

            # --------------------------------------------------
            # 5. Record neural activity snapshot
            # --------------------------------------------------

            step_activity = self.activity_collector.collect(
                step_index=step_index,
                action=action
            )

            step_activity["reversal"] = reversal

            self.activity_writer.append(step_activity)

            # --------------------------------------------------
            # 6. Apply action to environment
            # --------------------------------------------------

            next_state, metrics = self.simulator.step(state, action)

            metrics["reversal"] = reversal

            # --------------------------------------------------
            # 7. Record step outcome
            # --------------------------------------------------

            episode_history.append(
                {
                    "state": state,
                    "action": action,
                    "metrics": metrics,
                }
            )

            # update state
            state = next_state
            step_index += 1
            self.previous_action = action

        # --------------------------------------------------
        # Save neural activity trace
        # --------------------------------------------------

        if self.episode_dir:
            self.activity_writer.save(self.episode_dir)

        return episode_history

    def select_action(self):
        """
        Temporary exploration policy.

        Future replacement:
        - recall candidate strategies
        - arbitration
        - execution gate
        """

        return random.choice(ALL_ACTIONS)

    # --------------------------------------------------
    # ACTION REVERSAL DIAGNOSTIC
    # --------------------------------------------------

    def _detect_reversal(self, action: ActionType) -> bool:

        if self.previous_action is None:
            return False

        opposites = {
            ActionType.MOVE_NORTH: ActionType.MOVE_SOUTH,
            ActionType.MOVE_SOUTH: ActionType.MOVE_NORTH,
            ActionType.MOVE_EAST: ActionType.MOVE_WEST,
            ActionType.MOVE_WEST: ActionType.MOVE_EAST,
        }

        if action in opposites and self.previous_action == opposites[action]:
            return True

        return False