import math

from environment.policy_matrix import PolicyMatrix


class StimulusEncoder:
    """
    Translates WorldState into bounded neural stimulation and
    a directional navigation field.

    Design goals
    ------------
    - preserve smooth target attraction
    - preserve hazard repulsion
    - avoid deterministic wall-hugging traps
    - keep all effects bounded and inspectable
    """

    TRN_HAZARD_INTERRUPT = 0.249

    GRID_MIN = 0
    GRID_MAX = 10

    EDGE_STRENGTH = 0.175
    EDGE_RADIUS = 2.0

    def __init__(self):

        self.policy = PolicyMatrix()

    def encode(self, state, runtime):

        x, y = state.agent_position

        dir_x = 0.0
        dir_y = 0.0

        goal_dir_x = 0.0
        goal_dir_y = 0.0

        runtime.inject_stimulus("PFC", magnitude=0.08)

        # --------------------------------------------------
        # TARGET ATTRACTION
        # --------------------------------------------------

        if state.targets:

            tx, ty = state.targets[0]

            dx = tx - x
            dy = ty - y

            goal_dist = abs(dx) + abs(dy)

            base_value = 3.75 / (goal_dist + 2)
            halo_strength = 7.0 * math.exp(-1.4 * goal_dist)
            value_mag = base_value + halo_strength

            runtime.inject_stimulus("VTA", magnitude=value_mag)

            denom = max(goal_dist, 1)

            goal_dir_x = dx / denom
            goal_dir_y = dy / denom

            dir_x += goal_dir_x
            dir_y += goal_dir_y

            direction_gain = 1.2 + 1.0 * math.exp(-1.2 * goal_dist)

            runtime.inject_stimulus(
                "PFC_DIR_X",
                magnitude=goal_dir_x * direction_gain,
            )
            runtime.inject_stimulus(
                "PFC_DIR_Y",
                magnitude=goal_dir_y * direction_gain,
            )

            if goal_dist <= 1:
                runtime.inject_stimulus("PFC", magnitude=0.20)

        # --------------------------------------------------
        # HAZARD REPULSION + WALL-AWARE BYPASS
        # --------------------------------------------------

        if state.hazards:

            total_repulsion = 0.0
            repulse_x = 0.0
            repulse_y = 0.0

            for hx, hy in state.hazards:

                hazard_dist = abs(hx - x) + abs(hy - y)

                local = 1.3 * math.exp(-1.4 * hazard_dist)
                halo = 0.8 / (hazard_dist + 1)
                spike = 2.0 if hazard_dist == 0 else 0.0

                repulsion = local + halo + spike
                total_repulsion += repulsion

                # accumulate a continuous wall-scale repulsion field
                away_x = x - hx
                away_y = y - hy
                away_norm = max(abs(away_x) + abs(away_y), 1)

                repulse_x += (away_x / away_norm) * repulsion
                repulse_y += (away_y / away_norm) * repulsion

                if hazard_dist == 0:
                    runtime.inject_stimulus(
                        "TRN",
                        magnitude=self.TRN_HAZARD_INTERRUPT,
                    )

            runtime.inject_stimulus("AMYGDALA", magnitude=total_repulsion)

            # apply summed wall repulsion rather than nearest-hazard-only repulsion
            repulse_norm = max(abs(repulse_x) + abs(repulse_y), 1e-6)
            repulsion_gain = min(0.60, total_repulsion * 0.12)

            dir_x += (repulse_x / repulse_norm) * repulsion_gain
            dir_y += (repulse_y / repulse_norm) * repulsion_gain

            # derive two global tangents from the summed wall vector
            tan_a_x, tan_a_y = -repulse_y, repulse_x
            tan_b_x, tan_b_y = repulse_y, -repulse_x

            tan_a_x, tan_a_y = self._normalize_manhattan(tan_a_x, tan_a_y)
            tan_b_x, tan_b_y = self._normalize_manhattan(tan_b_x, tan_b_y)

            score_a = self._score_tangent(
                x=x,
                y=y,
                tan_x=tan_a_x,
                tan_y=tan_a_y,
                goal_dir_x=goal_dir_x,
                goal_dir_y=goal_dir_y,
                hazards=state.hazards,
            )

            score_b = self._score_tangent(
                x=x,
                y=y,
                tan_x=tan_b_x,
                tan_y=tan_b_y,
                goal_dir_x=goal_dir_x,
                goal_dir_y=goal_dir_y,
                hazards=state.hazards,
            )

            if score_a >= score_b:
                slip_x, slip_y = tan_a_x, tan_a_y
            else:
                slip_x, slip_y = tan_b_x, tan_b_y

            slip_gain = min(0.35, total_repulsion * 0.10)

            dir_x += slip_x * slip_gain
            dir_y += slip_y * slip_gain

        # --------------------------------------------------
        # ANTI-STAGNATION GOAL BIAS
        # --------------------------------------------------

        field_mag = abs(dir_x) + abs(dir_y)

        if field_mag < 0.35 and state.targets:

            tx, ty = state.targets[0]

            dx = tx - x
            dy = ty - y

            norm = max(abs(dx) + abs(dy), 1)

            dir_x += (dx / norm) * 0.18
            dir_y += (dy / norm) * 0.18        

        # --------------------------------------------------
        # MAP EDGE CONTAINMENT FORCE
        # --------------------------------------------------

        edge_strength = self.EDGE_STRENGTH
        edge_radius = self.EDGE_RADIUS

        if x < edge_radius:
            dir_x += edge_strength * (edge_radius - x)

        if x > self.GRID_MAX - edge_radius:
            dir_x -= edge_strength * (x - (self.GRID_MAX - edge_radius))

        if y < edge_radius:
            dir_y += edge_strength * (edge_radius - y)

        if y > self.GRID_MAX - edge_radius:
            dir_y -= edge_strength * (y - (self.GRID_MAX - edge_radius))

        # --------------------------------------------------
        # POLICY EMISSION
        # --------------------------------------------------

        policy_weights = self.policy.compute(dir_x, dir_y)

        runtime.policy_bias = policy_weights

        # optional debug hook; harmless if unused elsewhere
        runtime.navigation_field = {
            "dir_x": dir_x,
            "dir_y": dir_y,
            "goal_dir_x": goal_dir_x,
            "goal_dir_y": goal_dir_y,
        }

        # --------------------------------------------------
        # LOW-RESOURCE SALIENCE
        # --------------------------------------------------

        if state.resources < 5:
            runtime.inject_stimulus("SAL", magnitude=0.5)

    def _normalize_manhattan(self, x, y):

        denom = max(abs(x) + abs(y), 1)
        return x / denom, y / denom

    def _score_tangent(
        self,
        *,
        x,
        y,
        tan_x,
        tan_y,
        goal_dir_x,
        goal_dir_y,
        hazards,
    ):
        """
        Scores a tangent direction.

        Higher score is better.

        Components:
        - alignment with goal direction
        - inward preference away from map edges
        - avoid stepping directly into hazards
        """

        alignment = (tan_x * goal_dir_x) + (tan_y * goal_dir_y)

        next_x = x + self._step_sign(tan_x)
        next_y = y + self._step_sign(tan_y)

        edge_score = 0.0

        if next_x < self.GRID_MIN:
            edge_score -= 2.0
        elif next_x > self.GRID_MAX:
            edge_score -= 2.0
        elif next_x <= self.GRID_MIN + 1:
            edge_score -= 0.6
        elif next_x >= self.GRID_MAX - 1:
            edge_score -= 0.6

        if next_y < self.GRID_MIN:
            edge_score -= 2.0
        elif next_y > self.GRID_MAX:
            edge_score -= 2.0
        elif next_y <= self.GRID_MIN + 1:
            edge_score -= 0.6
        elif next_y >= self.GRID_MAX - 1:
            edge_score -= 0.6

        hazard_score = 0.0
        if (next_x, next_y) in hazards:
            hazard_score -= 3.0

        return alignment + edge_score + hazard_score

    def _step_sign(self, value):

        if value > 0:
            return 1
        if value < 0:
            return -1
        return 0