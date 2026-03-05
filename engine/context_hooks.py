# engine/context_hooks.py
from __future__ import annotations

from typing import Iterable, Optional

from engine.population_model import PopulationModel
from engine.runtime_context import RuntimeContext, GLOBAL_CONTEXT_KEY


class PFCContextHook:
    """
    PFC → RuntimeContext interface.

    FUNCTIONAL ROLE:
    - Interpret sustained PFC activity as task-relevant context
    - Translate activity into transient, gain-only bias
    - Provide working-memory-like influence across timesteps

    HARD GUARANTEES:
    - Gain-only (never writes activity or parameters)
    - Soft-thresholded (no brittle all-or-none gating)
    - Stateless (no memory inside the hook)
    - Decay handled exclusively by RuntimeContext

    SEMANTIC CONTRACT:
    - Assembly IDs from PFC are NOT assumed to align with downstream regions
    - By default, all injections target GLOBAL_CONTEXT_KEY
    - 'domain' selects the context channel, not the target assembly
    """

    def __init__(
        self,
        activity_threshold: float = 0.02,
        injection_gain: float = 0.05,
        target_domain: str = "global",
        max_inject_per_step: Optional[float] = None,
        inject_to_global: bool = True,
        enable_diagnostics: bool = False,
    ):
        # Threshold above baseline cortical noise
        self.activity_threshold = float(activity_threshold)

        # Linear gain applied to suprathreshold activity
        self.injection_gain = float(injection_gain)

        # Context domain (e.g. "global")
        self.target_domain = str(target_domain)

        # Optional safety cap (None = uncapped)
        self.max_inject_per_step = (
            None if max_inject_per_step is None else float(max_inject_per_step)
        )

        # If True, inject into GLOBAL_CONTEXT_KEY instead of per-assembly IDs
        self.inject_to_global = bool(inject_to_global)

        # Optional observability (off by default)
        self.enable_diagnostics = bool(enable_diagnostics)

        # Diagnostics (ephemeral, overwritten each apply)
        self.last_total_injected: float = 0.0
        self.last_contributors: int = 0

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def apply(
        self,
        pfc_assemblies: Iterable[PopulationModel],
        context: RuntimeContext,
        domain: Optional[str] = None,
    ) -> None:
        """
        Inspect PFC assemblies and inject context bias for those
        exceeding the activity threshold.

        MECHANISM:
        - Soft gating: (activity - threshold)
        - Linear scaling via injection_gain
        - Optional per-step cap
        - All decay handled by RuntimeContext

        TARGETING:
        - Default target is GLOBAL_CONTEXT_KEY to avoid silent consumer mismatch
        - 'domain' selects context channel, not assembly identity
        """
        dom = self.target_domain if domain is None else str(domain)

        total_injected = 0.0
        contributors = 0

        for p in pfc_assemblies:
            activity = float(p.output())

            # Soft threshold
            excess = activity - self.activity_threshold
            if excess <= 0.0:
                continue

            amount = self.injection_gain * excess

            if self.max_inject_per_step is not None:
                amount = min(amount, self.max_inject_per_step)

            target_id = GLOBAL_CONTEXT_KEY if self.inject_to_global else p.assembly_id

            # ✅ Correct RuntimeContext API call
            context.add_gain(
                target_id,
                amount,
                domain=dom,
            )

            total_injected += amount
            contributors += 1

        if self.enable_diagnostics:
            self.last_total_injected = total_injected
            self.last_contributors = contributors
