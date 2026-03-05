from __future__ import annotations

from typing import Dict, Any

# --------------------------------------------------
# Interpretive baseline storage (module-local)
# --------------------------------------------------
_REGION_MASS_BASELINE: Dict[str, float] = {}
_REGION_ACTIVITY_BASELINE: Dict[str, float] = {}
_BASELINE_LOCKED: bool = False


def collect_salience_observations(runtime) -> Dict[str, Any]:
    """
    Collect read-only salience-relevant observations from the runtime.

    CONTRACT:
    - Pure observation (no runtime mutation)
    - Interpretive state allowed (local baselines only)
    - No policy
    - No salience application
    - Safe to call every step

    OUTPUT SEMANTICS:
    - Emits FLATTENED structural channels (back-compat)
    - Emits NESTED delta maps for sources that expect them
      (SurpriseSource expects dict maps)
    - Emits DELTAS, not raw containers
    - Source-facing and stable
    """

    global _BASELINE_LOCKED

    obs: Dict[str, Any] = {}

    # --------------------------------------------------
    # Timebase (meta, explicitly non-surprising)
    # --------------------------------------------------
    obs["time"] = float(getattr(runtime, "time", 0.0))
    obs["dt"] = float(getattr(runtime, "dt", 0.0))

    # Provide a stable interpretive step if available
    step = getattr(runtime, "step_count", None)
    if step is not None:
        try:
            obs["step"] = int(step)
        except Exception:
            obs["step"] = -1
    else:
        obs["step"] = -1

    # --------------------------------------------------
    # Gate / BG state (read-only, optional)
    # --------------------------------------------------
    if hasattr(runtime, "snapshot_gate_state"):
        gate = runtime.snapshot_gate_state()
        obs["gate_relief"] = float(gate.get("relief", 1.0))
        obs["gate_winner"] = gate.get("winner")

    # --------------------------------------------------
    # Decision latch state (read-only)
    # --------------------------------------------------
    if hasattr(runtime, "get_decision_state"):
        obs["decision"] = runtime.get_decision_state()

    # --------------------------------------------------
    # Nested delta maps (required by SurpriseSource)
    # --------------------------------------------------
    region_mass_delta: Dict[str, float] = {}
    region_activity_delta: Dict[str, float] = {}

    # --------------------------------------------------
    # Structural region signals
    # --------------------------------------------------
    for region_key in getattr(runtime, "region_states", {}):
        snap = runtime.snapshot_region_stats(region_key)
        if not snap:
            continue

        # ------------------------------
        # Mean activity (diagnostic + delta baseline)
        # ------------------------------
        mean_activity = snap.get("mean")
        if mean_activity is not None:
            mean_activity = float(mean_activity)

            # Baseline capture (once per region)
            if not _BASELINE_LOCKED:
                _REGION_ACTIVITY_BASELINE.setdefault(region_key, mean_activity)

            act_base = _REGION_ACTIVITY_BASELINE.get(region_key)
            if act_base is not None:
                act_delta = mean_activity - float(act_base)
                region_activity_delta[region_key] = act_delta

            # Back-compat flattened diagnostic key
            obs[f"region_activity:{region_key}"] = mean_activity

        # ------------------------------
        # Mass + interpretive baseline
        # ------------------------------
        mass = snap.get("mass")
        if mass is None:
            continue

        mass = float(mass)

        # Baseline capture (once per region)
        if not _BASELINE_LOCKED:
            _REGION_MASS_BASELINE.setdefault(region_key, mass)

        mass_base = _REGION_MASS_BASELINE.get(region_key)
        if mass_base is None:
            continue

        # Structural deviation
        mass_delta = mass - float(mass_base)
        region_mass_delta[region_key] = mass_delta

        # Back-compat flattened delta key
        obs[f"region_mass:{region_key}"] = mass_delta

    # --------------------------------------------------
    # Publish nested maps for SurpriseSource
    # --------------------------------------------------
    obs["region_mass_delta"] = region_mass_delta
    obs["region_activity_delta"] = region_activity_delta

    # --------------------------------------------------
    # Lock baselines once at least one is captured
    # --------------------------------------------------
    if _REGION_MASS_BASELINE or _REGION_ACTIVITY_BASELINE:
        _BASELINE_LOCKED = True

    return obs
