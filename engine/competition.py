from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path
import time


class CompetitionKernel:
    """
    Channel-aware competition kernel.

    PURPOSE
    -------
    - Induce lateral competition across semantic channels (e.g. D1 vs D2)
    - Convert distributed assembly activity into smooth dominance signals
    - Provide stable, observable outputs for downstream BG / GPi gating

    DESIGN GUARANTEES
    -----------------
    - No learning
    - No oscillations
    - No hard winner-take-all
    - Fully bounded
    - Deterministic

    NOTE
    ----
    This kernel is *purely dynamical*. It must never:
    - latch decisions
    - store history beyond smooth dominance
    - receive feedback from commitment or action systems
    """

    # ============================================================
    # Trace logging (authoritative diagnostic channel)
    # ============================================================

    TRACE_PATH = Path(
        r"C:\Users\Admin\Desktop\neural framework\kernel_dominance_trace.csv"
    )

    _trace_initialized: bool = False
    _trace_step: int = 0

    # ============================================================
    # Init
    # ============================================================

    def __init__(
        self,
        inhibition_strength: float = 0.55,
        persistence_gain: float = 0.15,
        dominance_tau: float = 0.85,
        min_activity: float = 0.0,
        dominance_floor: float = 1e-6,
        contrast_gain: float = 1.0,
        epsilon_bias: float = 0.0,
        channel_key: str = "subpopulation",
    ):
        # Core parameters
        self.inhibition_strength = float(inhibition_strength)
        self.persistence_gain = float(persistence_gain)
        self.dominance_tau = max(float(dominance_tau), 1e-6)

        self.min_activity = float(min_activity)
        self.dominance_floor = float(dominance_floor)
        self.contrast_gain = float(contrast_gain)

        # Deterministic tie-breaking ONLY — never a bias signal
        self.epsilon_bias = float(epsilon_bias)

        self.channel_key = channel_key

        # Internal state: smoothed dominance per channel
        self._dominance: Dict[str, float] = {}

        # Diagnostics (public, read-only)
        self.last_global_dominance: float = 0.0
        self.last_winner_channel: Optional[str] = None
        self.last_dominance_map: Dict[str, float] = {}
        self.last_instantaneous_map: Dict[str, float] = {}
        self.last_channel_output: Dict[str, float] = {}

    # ============================================================
    # Public API
    # ============================================================

    def apply(
        self,
        assemblies: List,
        dt: float,
        external_gain: Optional[Dict[str, float]] = None,
        external_bias: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Apply channel-level competition.

        Parameters
        ----------
        assemblies:
            PopulationModel instances with semantic channel identity
        dt:
            Runtime timestep
        external_gain:
            Optional per-assembly gain (e.g. context modulation),
            aggregated strictly at the CHANNEL level
        external_bias:
            Optional per-channel additive bias (e.g. context / persistence)

        Returns
        -------
        float:
            Smoothed dominance value of winning channel
        """

        if not assemblies:
            self._clear_outputs()
            self._dominance.clear()
            return 0.0

        # --------------------------------------------------
        # 1. Group assemblies by semantic channel
        # --------------------------------------------------

        channels: Dict[str, List] = {}

        for a in assemblies:
            ch = getattr(a, self.channel_key, None) or "default"
            channels.setdefault(ch, []).append(a)

        # Retain dominance state only for live channels
        self._dominance = {ch: self._dominance.get(ch, 0.0) for ch in channels}

        # --------------------------------------------------
        # 2. Channel output + gain aggregation
        # --------------------------------------------------

        raw_output: Dict[str, float] = {}
        channel_gain: Dict[str, float] = {}

        for ch, plist in channels.items():
            total = 0.0
            gain_sum = 0.0
            gain_n = 0

            for p in plist:
                val = max(p.output(), self.min_activity)
                total += val

                if external_gain is not None:
                    gain_sum += external_gain.get(p.assembly_id, 1.0)
                    gain_n += 1

            raw_output[ch] = max(total, self.dominance_floor)
            channel_gain[ch] = gain_sum / gain_n if gain_n > 0 else 1.0

        # --------------------------------------------------
        # 3. Context modulation + bias (channel-level only)
        # --------------------------------------------------

        effective_output: Dict[str, float] = {}

        for ch, base in raw_output.items():
            gain_factor = 1.0 + self.contrast_gain * (channel_gain[ch] - 1.0)
            val = base * gain_factor

            if external_bias is not None:
                val += external_bias.get(ch, 0.0)

            effective_output[ch] = max(val, self.dominance_floor)

        total_output = sum(effective_output.values())
        if total_output <= 0.0:
            self._clear_outputs()
            return 0.0

        # --------------------------------------------------
        # 4. Instantaneous dominance (normalized)
        # --------------------------------------------------

        inst: Dict[str, float] = {
            ch: v / total_output for ch, v in effective_output.items()
        }

        # Deterministic epsilon ordering ONLY for exact ties
        if self.epsilon_bias > 0.0:
            for i, ch in enumerate(sorted(inst)):
                inst[ch] += self.epsilon_bias * (i + 1)
            norm = sum(inst.values())
            inst = {ch: v / norm for ch, v in inst.items()}

        # --------------------------------------------------
        # 5. Smooth dominance (first-order inertia)
        # --------------------------------------------------

        alpha = min(dt / self.dominance_tau, 1.0)

        for ch, d in inst.items():
            prev = self._dominance.get(ch, d)
            self._dominance[ch] = prev + alpha * (d - prev)

        # --------------------------------------------------
        # 6. Lateral inhibition (channel-level only)
        # --------------------------------------------------

        mean_dom = sum(self._dominance.values()) / len(self._dominance)

        for ch, plist in channels.items():
            own = self._dominance[ch]

            suppress = 0.0
            for och, od in self._dominance.items():
                if och != ch:
                    suppress += max(od - own, 0.0)

            if len(self._dominance) > 1:
                suppress /= (len(self._dominance) - 1)

            inhibition = self.inhibition_strength * suppress
            resistance = self.persistence_gain * max(
                self.contrast_gain * (own - mean_dom), 0.0
            )

            net = max(inhibition - resistance, 0.0)

            for p in plist:
                p.input -= net / max(len(plist), 1)

        # --------------------------------------------------
        # 7. Diagnostics snapshot
        # --------------------------------------------------

        winner_ch = max(self._dominance, key=self._dominance.get)
        winner_val = self._dominance[winner_ch]

        self.last_global_dominance = winner_val
        self.last_winner_channel = winner_ch
        self.last_dominance_map = dict(self._dominance)
        self.last_instantaneous_map = dict(inst)
        self.last_channel_output = dict(effective_output)

        # --------------------------------------------------
        # 8. Trace logging (ground truth)
        # --------------------------------------------------

        self._write_trace(inst, effective_output)

        return winner_val

    # ============================================================
    # Trace writer
    # ============================================================

    def _write_trace(
        self,
        inst: Dict[str, float],
        effective_output: Dict[str, float],
    ) -> None:
        """
        Append per-step dominance trace.
        One row per channel, per apply().
        """

        if not self.TRACE_PATH.parent.exists():
            self.TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)

        if not self._trace_initialized:
            with open(self.TRACE_PATH, "w", encoding="utf-8") as f:
                f.write(
                    "step,time,channel,effective_output,inst_dominance,"
                    "smooth_dominance,winner,delta\n"
                )
            self._trace_initialized = True

        self._trace_step += 1
        t = time.time()

        # Delta = top − runner-up (order independent, sign stable)
        if len(self._dominance) >= 2:
            vals = sorted(self._dominance.values(), reverse=True)
            delta = vals[0] - vals[1]
        else:
            delta = 0.0

        with open(self.TRACE_PATH, "a", encoding="utf-8") as f:
            for ch in self._dominance:
                f.write(
                    f"{self._trace_step},"
                    f"{t:.6f},"
                    f"{ch},"
                    f"{effective_output.get(ch, 0.0):.9f},"
                    f"{inst.get(ch, 0.0):.9f},"
                    f"{self._dominance.get(ch, 0.0):.9f},"
                    f"{self.last_winner_channel},"
                    f"{delta:.9f}\n"
                )

    # ============================================================
    # Diagnostics / Observability
    # ============================================================

    def format_diagnostics(self, precision: int = 7) -> str:
        if not self.last_dominance_map:
            return "CompetitionKernel: no dominance data"

        fmt = f"{{:.{precision}f}}"
        lines = ["CompetitionKernel diagnostics"]

        lines.append("  Effective channel output:")
        for ch, v in self.last_channel_output.items():
            lines.append(f"    {ch}: {fmt.format(v)}")

        lines.append("  Instantaneous dominance:")
        for ch, v in self.last_instantaneous_map.items():
            lines.append(f"    {ch}: {fmt.format(v)}")

        lines.append("  Smoothed dominance:")
        for ch, v in self.last_dominance_map.items():
            lines.append(f"    {ch}: {fmt.format(v)}")

        if len(self.last_dominance_map) >= 2:
            vals = sorted(self.last_dominance_map.values(), reverse=True)
            delta = vals[0] - vals[1]
            lines.append(f"  Dominance delta (top − runner-up): {fmt.format(delta)}")

        lines.append(f"  Winner: {self.last_winner_channel}")
        lines.append(f"  Winner value: {fmt.format(self.last_global_dominance)}")

        return "\n".join(lines)

    # ============================================================
    # Helpers
    # ============================================================

    def _clear_outputs(self) -> None:
        self.last_global_dominance = 0.0
        self.last_winner_channel = None
        self.last_dominance_map = {}
        self.last_instantaneous_map = {}
        self.last_channel_output = {}
