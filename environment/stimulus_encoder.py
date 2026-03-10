import math


class StimulusEncoder:
    """
    Translates WorldState into neural stimulation events.

    Uses:
        runtime.inject_stimulus(region_id, magnitude)
    """

    def encode(self, state, runtime):

        x, y = state.agent_position

        # --------------------------------------------------
        # POSITION SIGNAL → PFC
        # (light stabilization without strong origin attractor)
        # --------------------------------------------------

        pos_mag = 0.08 + abs(x) * 0.004 + abs(y) * 0.004
        runtime.inject_stimulus("PFC", magnitude=pos_mag)

        # --------------------------------------------------
        # TARGET PROXIMITY → VTA
        # (slightly stronger pull toward goal)
        # --------------------------------------------------

        if state.targets:

            tx, ty = state.targets[0]

            dist = abs(tx - x) + abs(ty - y)

            value_mag = 1.45 / (dist + 1)

            runtime.inject_stimulus("VTA", magnitude=value_mag)

        # --------------------------------------------------
        # HAZARD PROXIMITY → AMYGDALA
        # (smooth repulsion instead of hard zones)
        # --------------------------------------------------

        if state.hazards:

            hx, hy = state.hazards[0]

            dist = abs(hx - x) + abs(hy - y)

            # smooth decay repulsion
            urgency_mag = 2.2 * math.exp(-0.9 * dist)

            runtime.inject_stimulus("AMYGDALA", magnitude=urgency_mag)

        # --------------------------------------------------
        # LOW RESOURCES → SALIENCE
        # --------------------------------------------------

        if state.resources < 5:

            runtime.inject_stimulus("SAL", magnitude=0.5)