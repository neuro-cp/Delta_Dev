class StimulusEncoder:
    """
    Translates WorldState into neural stimulation events.

    This uses the BrainRuntime stimulus interface:
        runtime.inject_stimulus(region_id, magnitude)
    """

    def encode(self, state, runtime):

        x, y = state.agent_position

        # --------------------------------------------------
        # POSITION SIGNAL → PFC
        # --------------------------------------------------

        pos_mag = 0.1 + abs(x) * 0.02 + abs(y) * 0.02
        runtime.inject_stimulus("PFC", magnitude=pos_mag)

        # --------------------------------------------------
        # TARGET PROXIMITY → VTA (value signal)
        # --------------------------------------------------

        if state.targets:

            tx, ty = state.targets[0]

            dist = abs(tx - x) + abs(ty - y)

            value_mag = 1.0 / (dist + 1)

            runtime.inject_stimulus("VTA", magnitude=value_mag)

        # --------------------------------------------------
        # HAZARD PROXIMITY → AMYGDALA (urgency)
        # --------------------------------------------------

        if state.hazards:

            hx, hy = state.hazards[0]

            dist = abs(hx - x) + abs(hy - y)

            urgency_mag = 1.0 / (dist + 1)

            runtime.inject_stimulus("AMYGDALA", magnitude=urgency_mag)

        # --------------------------------------------------
        # LOW RESOURCES → SALIENCE
        # --------------------------------------------------

        if state.resources < 5:

            runtime.inject_stimulus("SAL", magnitude=0.5)