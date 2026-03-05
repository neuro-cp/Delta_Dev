# engine/salience/pre_decision_adaptation/adapter.py

from typing import Dict

from .psmem import PSMem


class PSMSalienceAdapter:
    """
    Adapter that translates Pre-Decision Salience Memory output
    into a one-shot multiplicative gain applied at episode start.

    This adapter:
      - is stateless across episodes
      - does NOT update memory
      - does NOT run per timestep
      - does NOT bypass salience or context policies
    """

    def __init__(self, psmem: PSMem) -> None:
        self.psmem = psmem

    def compute_gain_map(
        self,
        assembly_ids: list[str],
        context_id: str,
    ) -> Dict[str, float]:
        """
        Compute a per-assembly gain map to be cached for the episode.

        Returns:
            dict[assembly_id] -> gain (>= 1.0)
        """
        bias = self.psmem.get_bias(context_id)

        if bias <= 0.0:
            return {}

        gain = 1.0 + bias

        return {aid: gain for aid in assembly_ids}
