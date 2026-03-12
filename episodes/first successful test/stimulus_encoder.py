import math


class StimulusEncoder:
    """
    Translates WorldState into neural stimulation events.

    Uses
    ----
    runtime.inject_stimulus(region_id, magnitude)

    Design goals
    ------------
    • Target produces global attraction AND directional bias
    • Short-range halo sharpens final capture
    • Hazards produce repulsion without salience traps
    • TRN interrupts hazard attractor formation
    • Signals remain balanced so BG competition stays stable
    """

    TRN_HAZARD_INTERRUPT = 0.249

    def encode(self, state, runtime):

        x, y = state.agent_position

        # --------------------------------------------------
        # POSITION SIGNAL → PFC
        # weak stabilizing baseline
        # --------------------------------------------------

        runtime.inject_stimulus("PFC", magnitude=0.08)

        # --------------------------------------------------
        # TARGET SIGNAL → VTA + DIRECTIONAL CONTEXT
        # --------------------------------------------------

        if state.targets:

            tx, ty = state.targets[0]

            dx = tx - x
            dy = ty - y

            goal_dist = abs(dx) + abs(dy)

            # --------------------------------------------------
            # LONG-RANGE VALUE FIELD
            # keeps target globally relevant
            # --------------------------------------------------

            base_value = 3.75 / (goal_dist + 2)

            # --------------------------------------------------
            # SHORT-RANGE GOAL HALO
            # narrow radius, high local amplitude
            # --------------------------------------------------

            halo_strength = 7.0 * math.exp(-1.4 * goal_dist)

            value_mag = base_value + halo_strength
            runtime.inject_stimulus("VTA", magnitude=value_mag)

            # --------------------------------------------------
            # DIRECTIONAL CONTEXT
            # normalized direction vector
            # --------------------------------------------------

            denom = max(goal_dist, 1)

            dir_x = dx / denom
            dir_y = dy / denom

            # slight near-goal directional sharpening
            direction_gain = 1.2 + 1.0 * math.exp(-1.2 * goal_dist)

            runtime.inject_stimulus("PFC_DIR_X", magnitude=dir_x * direction_gain)
            runtime.inject_stimulus("PFC_DIR_Y", magnitude=dir_y * direction_gain)

            # --------------------------------------------------
            # VERY NEAR GOAL STABILIZATION
            # helps terminal capture without broad override
            # --------------------------------------------------

            if goal_dist <= 1:
                runtime.inject_stimulus("PFC", magnitude=0.20)

        # --------------------------------------------------
        # HAZARD FIELD → AMYGDALA
        # --------------------------------------------------

        if state.hazards:

            total_repulsion = 0.0

            for hx, hy in state.hazards:

                hazard_dist = abs(hx - x) + abs(hy - y)

                local = 1.3 * math.exp(-1.4 * hazard_dist)
                halo = 0.8 / (hazard_dist + 1)
                spike = 2.0 if hazard_dist == 0 else 0.0

                total_repulsion += local + halo + spike

                # --------------------------------------------------
                # TRN INTERRUPT
                # --------------------------------------------------

                if hazard_dist == 0:
                    runtime.inject_stimulus(
                        "TRN",
                        magnitude=self.TRN_HAZARD_INTERRUPT,
                    )

            runtime.inject_stimulus("AMYGDALA", magnitude=total_repulsion)

        # --------------------------------------------------
        # LOW RESOURCES → SALIENCE
        # --------------------------------------------------

        if state.resources < 5:
            runtime.inject_stimulus("SAL", magnitude=0.5)