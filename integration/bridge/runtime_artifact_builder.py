class RuntimeArtifactBuilder:

    def __init__(self, runtime):
        self.runtime = runtime

    def build_from_text(self, text: str, steps: int = 50):
        # minimal stimulus injection: treat text length as magnitude
        mag = float(len(text)) / 100.0

        # inject into a few global regions (safe generic entry)
        for region in ["PFC", "VTA", "AMYGDALA"]:
            try:
                self.runtime.inject_stimulus(region, magnitude=mag)
            except Exception:
                pass

        for _ in range(steps):
            self.runtime.step()

        return self._extract()

    def _extract(self):
        def safe(region):
            try:
                return self.runtime.snapshot_region_stats(region)["mass"]
            except Exception:
                return 0.0

        return {
            "pfc": safe("PFC"),
            "vta": safe("VTA"),
            "urgency": safe("AMYGDALA"),
        }
