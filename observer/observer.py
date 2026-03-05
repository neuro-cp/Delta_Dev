import json
import os
from typing import Dict, Any, Optional


class BrainObserver:
    """
    Observer / auditor for compiled brain definitions.

    RESPONSIBILITIES:
    - Summarize loaded regions and profiles
    - Validate region + population references
    - Provide human-readable diagnostics
    - Stay READ-ONLY (no runtime mutation)
    """

    def __init__(self, brain: Dict[str, Any]):
        self.brain = brain
        self.aliases = self._load_aliases()
        self._region_cache = self._build_region_cache()

    # --------------------------------------------------
    # Alias handling
    # --------------------------------------------------

    def _load_aliases(self) -> Dict[str, list]:
        """
        Load region alias definitions from regions/region_aliases.json
        """
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "regions",
            "region_aliases.json",
        )

        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("aliases", {})
        except FileNotFoundError:
            return {}
        except Exception as e:
            print(f"⚠️  Alias file error: {e}")
            return {}

    def _build_region_cache(self) -> Dict[str, str]:
        """
        Build a fast lookup map for region resolution:
        lowercased_label -> canonical_region_key
        """
        regions = self.brain.get("regions", {})
        cache: Dict[str, str] = {}

        for key, region in regions.items():
            cache[key.lower()] = key

            if isinstance(region, dict):
                rid = region.get("region_id")
                name = region.get("name")

                if rid:
                    cache[str(rid).lower()] = key
                if name:
                    cache[str(name).lower()] = key

        # Aliases
        for canonical, members in self.aliases.items():
            for m in members:
                if m.lower() in cache:
                    cache[canonical.lower()] = cache[m.lower()]

        return cache

    def _resolve_region(self, name: Optional[str]) -> Optional[str]:
        """
        Resolve a region name / alias / label to a canonical region key.
        """
        if not name:
            return None

        return self._region_cache.get(str(name).lower())

    # --------------------------------------------------
    # High-level summaries
    # --------------------------------------------------

    def summary(self) -> None:
        """
        Print a compact summary of the brain definition.
        """
        print("\n=== BRAIN SUMMARY ===")

        neuron_bases = self.brain.get("neuron_bases", {})
        regions = self.brain.get("regions", {})

        print(f"Neuron base files loaded: {len(neuron_bases)}")
        print(f"Regions loaded: {len(regions)}")

        print("\nRegions:")
        for region_id in sorted(regions.keys()):
            print(f"  - {region_id}")

        expr = self.brain.get("expression_profile")
        state = self.brain.get("state_profile")
        compound = self.brain.get("compound_profile")

        print("\nActive Profiles:")
        print(f"  Expression: {expr.get('profile_name') if expr else 'None'}")
        print(f"  State: {state.get('state_name') if state else 'None'}")
        print(f"  Compound: {compound.get('compound_name') if compound else 'None'}")

        print("\n====================\n")

    # --------------------------------------------------
    # Structural inspection
    # --------------------------------------------------

    def region_details(self) -> None:
        """
        Print per-region population composition (counts only).
        """
        print("\n=== REGION DETAILS ===")

        regions = self.brain.get("regions", {})

        for region_id, region in regions.items():
            print(f"\n[{region_id.upper()}]")

            populations = region.get("populations", {})
            if not populations:
                print("  No populations defined")
                continue

            total_neurons = 0
            for pop_name, pop in populations.items():
                count = int(pop.get("count", 0) or 0)
                ntype = pop.get("neuron_type", "unknown")
                total_neurons += count
                print(f"  - {pop_name}: {count} ({ntype})")

            print(f"  Total neurons: {total_neurons}")

        print("\n======================\n")

    # --------------------------------------------------
    # Connectivity inspection
    # --------------------------------------------------

    def connectivity_summary(self) -> None:
        """
        Print region-to-region connectivity graph (human readable).
        """
        print("\n=== CONNECTIVITY SUMMARY ===")

        regions = self.brain.get("regions", {})

        for region_id, region in regions.items():
            outputs = region.get("outputs", [])
            inputs = region.get("inputs", [])

            if not outputs and not inputs:
                continue

            print(f"\n[{region_id.upper()}]")

            if inputs:
                print("  Inputs:")
                for inp in inputs:
                    src = inp.get("source_region", "unknown")
                    strength = inp.get("strength", "?")
                    print(f"    <- {src} (strength {strength})")

            if outputs:
                print("  Outputs:")
                for out in outputs:
                    tgt = out.get("target_region", "unknown")
                    strength = out.get("strength", "?")
                    print(f"    -> {tgt} (strength {strength})")

        print("\n============================\n")

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def validate_references(self) -> None:
        """
        Validate region and population references.
        Does NOT stop execution — purely diagnostic.
        """
        print("\n=== REFERENCE VALIDATION ===")

        regions = self.brain.get("regions", {})
        warnings = 0
        infos = 0

        for region_id, region in regions.items():
            inputs = region.get("inputs", [])
            outputs = region.get("outputs", [])

            # ---- Inputs ----
            for inp in inputs:
                src = inp.get("source_region")
                resolved = self._resolve_region(src)

                if src and not resolved:
                    print(
                        f"⚠️  WARNING: [{region_id}] input source_region '{src}' not resolved"
                    )
                    warnings += 1
                elif src and resolved and resolved != src:
                    print(
                        f"ℹ️  INFO: [{region_id}] input '{src}' resolved to '{resolved}'"
                    )
                    infos += 1

                src_pop = inp.get("source_population")
                if src_pop and resolved:
                    pops = regions[resolved].get("populations", {})
                    if src_pop not in pops:
                        print(
                            f"⚠️  WARNING: [{region_id}] source_population '{src_pop}' not found in region '{resolved}'"
                        )
                        warnings += 1

            # ---- Outputs ----
            for out in outputs:
                tgt = out.get("target_region")
                resolved = self._resolve_region(tgt)

                if tgt and not resolved:
                    print(
                        f"⚠️  WARNING: [{region_id}] output target_region '{tgt}' not resolved"
                    )
                    warnings += 1
                elif tgt and resolved and resolved != tgt:
                    print(
                        f"ℹ️  INFO: [{region_id}] output '{tgt}' resolved to '{resolved}'"
                    )
                    infos += 1

                tgt_pop = out.get("target_population")
                if tgt_pop and resolved:
                    pops = regions[resolved].get("populations", {})
                    if tgt_pop not in pops:
                        print(
                            f"⚠️  WARNING: [{region_id}] target_population '{tgt_pop}' not found in region '{resolved}'"
                        )
                        warnings += 1

        if warnings == 0:
            print("✓ No unresolved references")

        print(
            f"\nValidation complete — {warnings} warning(s), {infos} info resolution(s)\n"
        )
