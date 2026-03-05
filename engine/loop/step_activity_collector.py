import time


class StepActivityCollector:
    """
    Collects region-level runtime activity at a single step.

    Pure observer. Never mutates runtime.
    """

    TOP_K = 5  # number of highest-activity assemblies to record

    def __init__(self, runtime):
        self.runtime = runtime

    def collect(self, step_index: int, action=None):

        region_activity = {}

        for region_key, region in self.runtime.region_states.items():

            stats = self.runtime.snapshot_region_stats(region_key)

            # --------------------------------------------------
            # Gather assembly activity values
            # --------------------------------------------------

            activities = []
            indexed_activities = []

            idx = 0

            for plist in region["populations"].values():
                for pop in plist:
                    act = float(getattr(pop, "activity", 0.0))
                    activities.append(act)
                    indexed_activities.append((idx, act))
                    idx += 1

            # --------------------------------------------------
            # Compute fraction_active
            # --------------------------------------------------

            fraction_active = None

            if activities:
                mean = sum(activities) / len(activities)
                active = sum(1 for v in activities if v > mean)
                fraction_active = active / len(activities)

            stats["fraction_active"] = fraction_active

            # --------------------------------------------------
            # Compute top assemblies
            # --------------------------------------------------

            top_assemblies = []

            if indexed_activities:

                # sort descending by activity
                indexed_activities.sort(key=lambda x: x[1], reverse=True)

                top_assemblies = [
                    idx for idx, _ in indexed_activities[: self.TOP_K]
                ]

            stats["top_assemblies"] = top_assemblies

            region_activity[region_key] = stats

        return {
            "step": step_index,
            "timestamp": time.time(),
            "action": str(action) if action else None,
            "regions": region_activity,
        }