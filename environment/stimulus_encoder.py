import math


class StimulusEncoder:
    """
    Translates WorldState into neural stimulation events.

    Uses:
        runtime.inject_stimulus(region_id, magnitude)

    Design goals
    ------------
    • Target produces smooth global attraction
    • Hazards produce repulsion without creating salience traps
    • Signals remain balanced so BG competition stays stable
    """

    def encode(self, state, runtime):

        x, y = state.agent_position

        # --------------------------------------------------
        # POSITION SIGNAL → PFC
        # stabilization only (no outward drift)
        # --------------------------------------------------

        pos_mag = 0.08
        runtime.inject_stimulus("PFC", magnitude=pos_mag)

        # --------------------------------------------------
        # TARGET PROXIMITY → VTA
        # stronger long-range attractor
        # --------------------------------------------------

        if state.targets:

            tx, ty = state.targets[0]

            dist = abs(tx - x) + abs(ty - y)

            value_mag = 3.5 / (dist + 2)

            runtime.inject_stimulus("VTA", magnitude=value_mag)

        # --------------------------------------------------
        # HAZARD FIELD → AMYGDALA
        # repulsion without salience capture
        # --------------------------------------------------

        if state.hazards:

            total_repulsion = 0.0

            for hx, hy in state.hazards:

                dist = abs(hx - x) + abs(hy - y)

                local = 1.3 * math.exp(-1.4 * dist)

                halo = 0.8 / (dist + 1)

                spike = 2.0 if dist == 0 else 0.0

                total_repulsion += local + halo + spike

                # --------------------------------------------------
                # TRN INHIBITORY INTERRUPT
                # collapse PFC attractor if hazard touched
                # --------------------------------------------------

                if dist == 0:
                    runtime.inject_stimulus("TRN", magnitude=0.245)

            runtime.inject_stimulus("AMYGDALA", magnitude=total_repulsion)

        # --------------------------------------------------
        # LOW RESOURCES → SALIENCE
        # --------------------------------------------------

        if state.resources < 5:

            runtime.inject_stimulus("SAL", magnitude=0.5)