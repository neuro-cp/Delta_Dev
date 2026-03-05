
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from engine.population_model import PopulationModel
from engine.competition import CompetitionKernel
from engine.runtime_context import RuntimeContext
from engine.context_hooks import PFCContextHook
from engine.salience.salience_field import SalienceField
from persistence.persistence_core import BasalGangliaPersistence
from engine.decision_bias import DecisionBias
from engine.decision_fx.adapter import DecisionFXAdapter
from memory.working_state.pfc_adapter import PFCAdapter
from engine.execution.execution_target import ExecutionTarget
from engine.control.control_hook import ControlHook
from engine.control.control_state import ControlState
from engine.vta_value.value_signal import ValueSignal
from engine.vta_value.value_adapter import ValueAdapter
from engine.vta_value.value_trace import ValueTrace
from engine.affective_urgency.urgency_signal import UrgencySignal
from engine.affective_urgency.urgency_policy import UrgencyPolicy
from engine.affective_urgency.urgency_trace import UrgencyTrace
from engine.affective_urgency.urgency_adapter import UrgencyAdapter
from engine.routing.hypothesis_registry import HypothesisRegistry
from engine.routing.hypothesis_router import HypothesisRouter
from engine.routing.hypothesis_generator import HypothesisGenerator
from engine.routing.hypothesis_pressure import HypothesisPressure







# ============================================================
# Utilities
# ============================================================

def _norm(x: Any) -> str:
    return str(x or "").strip().lower()


def _as_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


# ============================================================
# BrainRuntime
# ============================================================

class BrainRuntime:
    """
    Ground-truth dynamical runtime.

    EXECUTION ORDER (AUTHORITATIVE):
      1. Reset inputs + apply stimuli
      2. Physiology update
      3. PFC → RuntimeContext injection
      4. Striatum competition + BG persistence
      5. Context / salience decay
      6. GPi disinhibition
      7. Connectivity propagation + Thalamic gating

    ADDITIONS:
      - Read-only decision latch ideal: .04,.47,5
      - Advisory Decision FX (post-commit, thalamic only)
    """

    DECISION_DOMINANCE_THRESHOLD = 0.04
    DECISION_RELIEF_THRESHOLD = 0.47
    DECISION_SUSTAIN_STEPS = 5

    def __init__(self, brain: Dict[str, Any], dt: float = 0.01):
        self.brain = brain
        self.dt = float(dt)
        self.time = 0.0
        self.step_count = 0

        # ------------------------------------------------------------
        # TEST-ONLY: decision coincidence injection
        # ------------------------------------------------------------
        self._test_coincidence_enabled = False
        self._test_delta_boost = 0.0
        self._test_relief_boost = 0.0
        self._test_coincidence_steps = 0

        # ---------------- Global defaults ----------------
        gd = brain.get("global_dynamics", {}) or {}
        self.global_pop_dyn = gd.get("population_defaults", {})

        # ---------------- Assembly control ----------------
        self.assembly_control = self._load_assembly_control()

        # ---------------- Competition ----------------
        self.enable_competition = True
        self.competition_kernel = CompetitionKernel(
            inhibition_strength=0.55,
            persistence_gain=0.15,
            dominance_tau=0.75,
        )

        # ---------------- BG persistence ----------------
        self.enable_persistence = True
        self.bg_persistence = BasalGangliaPersistence(
            decay_tau=30.0,
            bias_gain=0.15,
        )

        # ---------------- Context ----------------
        self.enable_context = True
        self.context = RuntimeContext(decay_tau=5.0)

        self.enable_pfc_context = True
        self.pfc_context = PFCContextHook(
            activity_threshold=0.02,
            injection_gain=0.05,
            target_domain="global",
        )

        # ---------------- Salience ----------------
        self.enable_salience = True
        self.salience = SalienceField(decay_tau=3.0)
        
        # ---------------- Pre-decision salience adaptation ----------------
        self.enable_pre_decision_adaptation = False  # off by default
        self._psm_gain_cache: Dict[str, float] = {}

        # ---------------- Decision bias ----------------
        self.enable_decision_bias = True
        self.decision_bias = DecisionBias(
            decay_tau=4.0,
            max_bias=0.30,
            suppress_gain=0.15,
        )

        # ---------------- Decision FX ----------------
        self.enable_decision_fx = True
        self.decision_fx = DecisionFXAdapter(enable_trace=True)

        # ---------------- VTA Value (Phase 3A) ----------------
        self.enable_vta_value = True
        from engine.vta_value.value_policy import ValuePolicy

        self.value_policy = ValuePolicy()

        self.value_signal = ValueSignal(
            decay_tau=6.0,   # slower than salience, faster than memory
        )
        self.value_adapter = ValueAdapter(
            decision_bias_gain=0.5,
            pfc_persistence_gain=0.3,
        )
        self.value_trace = ValueTrace()

        # ---------------- Affective Urgency (Phase 3B) ----------------
        self.enable_urgency = False  # OFF by default

        self.urgency_signal = UrgencySignal(
            rise_rate=0.0,
            decay_rate=0.0,
            enabled=False,
        )

        self.urgency_policy = UrgencyPolicy(
            min_gate_relief=0.0,
            max_gate_relief=1.0,
            max_urgency=1.0,
        )

        self.urgency_trace = UrgencyTrace()

        self.urgency_adapter = UrgencyAdapter(
            signal=self.urgency_signal,
            policy=self.urgency_policy,
            trace=self.urgency_trace,
        )

        # ---------------- PFC working state adapter ----------------
        self.enable_pfc_adapter = True
        self.pfc_adapter = PFCAdapter(enable=True)
      
        # ---------------- GPi gating ----------------
        self.enable_gpi_disinhibition = True
        self.gpi_gain = 0.6
        self.gpi_floor = 0.25
        self._last_gate_strength: float = 1.0

        # ---------------- Runtime state ----------------
        self.region_states: Dict[str, Dict[str, Any]] = {}
        self._all_pops: List[PopulationModel] = []
        self._stim_queue: List[Tuple[str, Optional[str], Optional[int], float]] = []
        self._region_key_by_label: Dict[str, str] = {}
        self._urgency_gain: float = 1.0

        # ---------------- Decision latch ----------------
        self._decision_fired = False
        self._decision_counter = 0
        self._decision_state: Optional[Dict[str, Any]] = None
        self._control_state: Optional[ControlState] = None

        self._decision_sustain_required = int(self.DECISION_SUSTAIN_STEPS)
        latch_cfg = brain.get("decision_latch", {}) or {}
        if "sustain_steps" in latch_cfg:
            self._decision_sustain_required = max(
                1, int(latch_cfg["sustain_steps"])
            )

        self._build(brain)

        # ---------------- Assembly differentiation (STRUCTURAL, compile-time) ----------------
        try:
            from regions.assembly_differentiation.adapter import (
                AssemblyDifferentiationAdapter,
            )

            AssemblyDifferentiationAdapter.apply(runtime=self)
        except ImportError:
            # Differentiation layer not present; safe no-op
            pass


        # ---------------- Hypothesis routing (STRUCTURAL) ----------------
        self.hypothesis_registry = HypothesisRegistry()
        self.hypothesis_router = HypothesisRouter(self.hypothesis_registry)
        
        # ---------------- Hypothesis generation (STRUCTURAL) ----------------
        self.hypothesis_generator = HypothesisGenerator()
       
        # ---------------- Hypothesis pressure (STRUCTURAL, read-only) ----------------
        self.hypothesis_pressure = HypothesisPressure()

        # ---------------- Routing influence (STRUCTURAL, gain-only) ----------------
        from engine.routing.routing_influence import RoutingInfluence

        self.routing_influence = RoutingInfluence(
            default_gain=1.0
        )

        # ---------------- Execution gate ----------------
        from engine.execution.execution_state import ExecutionState
        from engine.execution.execution_gate import ExecutionGate

        toggle_path = Path(__file__).parent.parent / "config" / "executive_function_toggle.json"

        enabled_flag = False  # safe default

        if toggle_path.exists():
            try:
                with open(toggle_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    enabled_flag = bool(data.get("enabled", False))
            except Exception:
                enabled_flag = False  # fail closed

        self.execution_state = ExecutionState(enabled=enabled_flag)
        self.execution_gate = ExecutionGate(self.execution_state)

        # ---------------- Recall → Runtime bridge ----------------
        try:
            from memory.recall_runtime_bridge.recall_runtime_adapter import (
                RecallRuntimeAdapter,
            )

            self.recall_runtime_adapter = RecallRuntimeAdapter()
        except ImportError:
            self.recall_runtime_adapter = None

        # ---------------- Observation hook (READ-ONLY) ----------------
        try:
            from engine.observation.observation_runtime_hook import (
                ObservationRuntimeHook,
            )
            self._observation_hook = ObservationRuntimeHook()
        except ImportError:
            # Observation layer not present; safe no-op
            self._observation_hook = None
       

        # ---------------- Episodic boundary (READ-ONLY) ----------------
        try:
            from memory.episodic.episode_trace import EpisodeTrace
            from memory.episodic.episode_tracker import EpisodeTracker
            from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook
            from memory.episodic_boundary.boundary_adapter import BoundaryAdapter

            # Episodic trace is the forensic ledger (immutable, append-only)
            self._episode_trace = EpisodeTrace()

            # Tracker owns episode lifecycle, backed by trace
            self._episode_tracker = EpisodeTracker(
                trace=self._episode_trace
            )

            # Boundary adapter interprets observation → boundary events
            self._episodic_boundary_adapter = BoundaryAdapter()

            # Runtime hook applies declared boundary events to tracker
            self._episode_runtime_hook = EpisodeRuntimeHook(
                tracker=self._episode_tracker
            )

        except ImportError:
            # Episodic boundary layer not present; safe no-op
            self._episode_trace = None
            self._episode_tracker = None
            self._episodic_boundary_adapter = None
            self._episode_runtime_hook = None

    # ============================================================
    # Assembly Control
    # ============================================================

    def _load_assembly_control(self) -> Dict[str, int]:
        path = Path(__file__).parent.parent / "config" / "assembly_control.json"
        if not path.exists():
            return {}

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        out: Dict[str, int] = {}
        for region, spec in raw.items():
            try:
                n = int(spec["assemblies"] if isinstance(spec, dict) else spec)
                out[region.lower()] = max(1, n)
            except Exception:
                pass
        return out

    # ============================================================
    # Region Resolution
    # ============================================================

    def _build_region_id_map(self, regions: Dict[str, Any]) -> None:
        self._region_key_by_label.clear()
        for key, rdef in regions.items():
            self._region_key_by_label[_norm(key)] = key
            if isinstance(rdef, dict) and rdef.get("region_id"):
                self._region_key_by_label[_norm(rdef["region_id"])] = key

    def _resolve_region_key(self, label: str) -> Optional[str]:
        return self._region_key_by_label.get(_norm(label))

    # ============================================================
    # Build Network
    # ============================================================

    def _build(self, brain: Dict[str, Any]) -> None:
        regions = brain.get("regions", {}) or {}
        self._build_region_id_map(regions)

        for region_key, region_def in regions.items():
            self.region_states[region_key] = {
                "def": region_def,
                "populations": {},
            }

            n_assemblies = self.assembly_control.get(region_key.lower())
            if n_assemblies is None:
                continue

            for pop_id, pop_blob in region_def.get("populations", {}).items():
                count = _as_int(pop_blob.get("count"), 0)
                if count <= 0:
                    continue

                size = max(1, count // n_assemblies)
                plist: List[PopulationModel] = []

                for i in range(n_assemblies):
                    params = dict(self.global_pop_dyn)
                    params.update(pop_blob)
                    params["size"] = size

                    pop = PopulationModel.from_params(
                        params,
                        default_assembly_id=f"{region_key}:{pop_id}:{i}",
                        global_defaults=self.global_pop_dyn,
                    )
                    plist.append(pop)
                    self._all_pops.append(pop)

                self.region_states[region_key]["populations"][pop_id] = plist

    # ============================================================
    # External Input API
    # ============================================================

    def inject_stimulus(
        self,
        region_id: str,
        population_id: Optional[str] = None,
        assembly_index: Optional[int] = None,
        magnitude: float = 1.0,
    ) -> None:
        rk = self._resolve_region_key(region_id) or region_id
        self._stim_queue.append((rk, population_id, assembly_index, magnitude))

    # ============================================================
    # STEP
    # ============================================================

    def step(self) -> None:
        self.step_count += 1

        # ============================================================
        # STEP (AUTHORITATIVE ORDER)
        # ============================================================

        # ------------------------------------------------------------
        # Urgency init (safe default)
        # ------------------------------------------------------------
        urgency = 0.0
        self._urgency_gain = 1.0

        # 1. Reset inputs + apply stimuli
        for p in self._all_pops:
            p.input = 0.0

        for region_key, pop_id, idx, mag in self._stim_queue:
            pops = self.region_states.get(region_key, {}).get("populations", {})
            targets = pops.values() if pop_id is None else [pops.get(pop_id, [])]

            for plist in targets:
                for p in plist if idx is None else plist[idx:idx + 1]:
                    gain = 1.0
                    if self.enable_pre_decision_adaptation:
                        gain *= self._psm_gain_cache.get(p.assembly_id, 1.0)
                    if self.enable_context:
                        gain *= self.context.get_gain(p.assembly_id)
                    if self.enable_salience:
                        sal = self.salience.get(p.assembly_id)
                        if self.enable_urgency:
                            sal *= (1.0 + urgency)
                        gain *= (1.0 + sal)
                    p.input += mag * gain

        self._stim_queue.clear()

        # 2. Physiology update
        for p in self._all_pops:
            p.step(self.dt)

        # 2b. Hypothesis observation (cortical only, read-only) ---
        assoc = self.region_states.get("association_cortex")
        if assoc and hasattr(self, "hypothesis_generator"):
            assemblies = [
                p for plist in assoc["populations"].values() for p in plist
            ]
            self.hypothesis_generator.observe(assemblies)


        # 3. Striatum competition + BG persistence
        if self.enable_competition:
            self._step_striatum()

        # 4. GPi disinhibition (gate computation)
        relief = self._compute_gpi_relief()
        self._last_gate_strength = relief

        # 4a. Hypothesis pressure (pre-decision, read-only)
        hypothesis_pressure = {}

        if hasattr(self, "hypothesis_pressure"):
            snap = getattr(self, "_last_striatum_snapshot", {}) or {}
            dominance = snap.get("dominance", {})

            assoc = self.region_states.get("association_cortex")
            if assoc:
                assemblies = {
                    p.assembly_id: p.output()
                    for plist in assoc["populations"].values()
                    for p in plist
                }

                hypothesis_pressure = self.hypothesis_pressure.compute(
                    gate_relief=relief,
                    dominance=dominance,
                    assemblies=assemblies,
                )

        # 4b. Affective urgency (read-only, pre-decision)
        if self.enable_urgency:
            snap = getattr(self, "_last_striatum_snapshot", {}) or {}
            dom = snap.get("dominance", {})
            delta = 0.0
            if len(dom) >= 2:
                vals = sorted(dom.values(), reverse=True)
                delta = vals[0] - vals[1]

            urgency = self.urgency_adapter.compute(
                time=self.time,
                step=self.step_count,
                dt=self.dt,
                gate_relief=relief,
                dominance_delta=delta,
            )

            self._urgency_gain = 1.0 + urgency

        # 5. Striatum → decision bias (value × urgency tempo)
        if self.enable_vta_value and self.enable_decision_bias:
            urgency_gain = 1.0 + urgency if self.enable_urgency else 1.0

            raw_value = self.value_signal.get() * urgency_gain

            # ---------------- Recall injection (VALUE_BIAS) ----------------
            recall_bias_value = 0.0

            if (
                self.execution_state.enabled
                and self.recall_runtime_adapter is not None
            ):
                packet = self._compute_recall_packet()

                bridge_result = self.recall_runtime_adapter.apply_packet(
                    packet=packet,
                    gate=self.execution_gate,
                    identity_map={"VALUE_BIAS": 0.0},
                )

                recall_bias_value = bridge_result.applied_targets.get(
                    "VALUE_BIAS", 0.0
                )

            combined_value = raw_value + recall_bias_value

            gated_value = self.execution_gate.apply(
                target=ExecutionTarget.VALUE_BIAS,
                value=combined_value,
                identity=0.0,
            )

            self.decision_bias.apply_external(
                lambda bias_map: self.value_adapter.apply_to_decision_bias(
                    value=gated_value,
                    bias_map=bias_map,
                )
            )

        # 6. Decision latch (creates _decision_state)
        self._evaluate_decision_latch(relief)

        # 6a. Episodic observation (READ-ONLY, Phase 5)
        if hasattr(self, "episode_hook"):
            decision_event = self._decision_state is not None
            self.episode_hook.step(
                step=self.step_count,
                decision_event=decision_event,
                context_shift=False,  # future hook
            )

        # 6b. Hypothesis proposal (registration only, no routing)
        if hasattr(self, "hypothesis_generator"):
            proposals = self.hypothesis_generator.propose(
                pressure=hypothesis_pressure
            )
            for aid, hid in proposals.items():
                self.hypothesis_registry.register(aid, hid)

        # 6c. control snapshot (read-only, post-decision)
        self._control_state = ControlHook.compute(self)


        # 7. PFC → Context injection (now sees working state)
        if self.enable_context and self.enable_pfc_context:
            self._apply_pfc_context()

        # 8. Decay (context, salience, bias, working state)
        if self.enable_vta_value:
            self.value_signal.step(self.dt)
        if self.enable_context:
            self.context.step(self.dt)
        if self.enable_salience:
            self.salience.step(self.dt)
        if self.enable_decision_bias:
            self.decision_bias.step(self.dt)

        if self.enable_pfc_adapter:
            self.pfc_adapter.step(self.dt)

            if self.enable_vta_value:
                urgency_gain = 1.0 + urgency if self.enable_urgency else 1.0
                self.pfc_adapter.apply_external_gain(
                    lambda base_gain: self.value_adapter.apply_to_pfc_persistence(
                        value=self.value_signal.get() * urgency_gain,
                        base_gain=base_gain,
                    )
                )

        # 9. Decision FX (post-commit, advisory only)
        if self.enable_decision_fx and self._decision_state is not None:
            self.decision_fx.apply(
                decision_state=self._decision_state,
                dominance=getattr(self, "_last_striatum_snapshot", {}).get("dominance", {}),
            )

        # 10. Connectivity propagation + thalamic gating
        self._propagate_connectivity(relief)

        # 12. Advance time
        self.time += self.dt
        
        # ---------------- Observation (READ-ONLY, post-settle) ----------------
        if self._observation_hook is not None:
            self._observation_hook.step(self)
        
        # ---------------- Episodic boundary (READ-ONLY, post-observation) ----------------
        if (
            self._episode_runtime_hook is not None
            and self._episodic_boundary_adapter is not None
            and self._observation_hook is not None
        ):
            boundary_events = self._episodic_boundary_adapter.step(
                step=self.step_count,
                observation_events=self._observation_hook.events,
            )

            self._episode_runtime_hook.step(
                step=self.step_count,
                boundary_events=boundary_events,
            )

    # ============================================================
    # Subsystems
    # ============================================================
    
    def value_set(self, x: float) -> None:
        """
        Policy-gated value setter.
        Mirrors the command server's value_set behavior.
        Intended for tests and controlled experiments.
        """
        val = getattr(self, "value_signal", None)
        pol = getattr(self, "value_policy", None)

        if not val or not pol or not self.enable_vta_value:
            return

        new_val = pol.apply(
            current_value=val.get(),
            proposed_value=float(x),
            t=self.time,
        )
        val.set(new_val)

    # ============================================================
    # Pre-decision adaptation helpers
    # ============================================================

    def clear_pre_decision_adaptation(self) -> None:
        """
        Clear cached PSM gains.
        Call this at episode boundaries (e.g. reset_latch).
        """
        self._psm_gain_cache.clear()
        self._test_coincidence_enabled = False
        self._test_delta_boost = 0.0
        self._test_relief_boost = 0.0
        self._test_coincidence_steps = 0


    
    
    def _apply_pfc_context(self) -> None:
        pfc = self.region_states.get("pfc")
        if not pfc:
            return

        assemblies = [p for plist in pfc["populations"].values() for p in plist]
        if assemblies:
            self.pfc_context.apply(assemblies, self.context)

        # PFC working-state gain (advisory, post-decision)
        if self.enable_pfc_adapter and self.pfc_adapter.is_engaged():
            raw_gain = self.pfc_adapter.strength()

            # ---------------- Recall injection (PFC_CONTEXT_GAIN) ----------------
            recall_context_gain = 0.0

            if (
                self.execution_state.enabled
                and self.recall_runtime_adapter is not None
            ):
                packet = self._compute_recall_packet()

                bridge_result = self.recall_runtime_adapter.apply_packet(
                    packet=packet,
                    gate=self.execution_gate,
                    identity_map={"PFC_CONTEXT_GAIN": 1.0},
                )

                recall_context_gain = bridge_result.applied_targets.get(
                    "PFC_CONTEXT_GAIN", 0.0
                )

            combined_gain = raw_gain + recall_context_gain

            gated_gain = self.execution_gate.apply(
                target=ExecutionTarget.PFC_CONTEXT_GAIN,
                value=combined_gain,
                identity=1.0,
            )

                   
    def _step_striatum(self) -> None:
        striatum = self.region_states.get("striatum")
        if not striatum:
            return

        assemblies = []
        for plist in striatum["populations"].values():
            for p in plist:
                if getattr(p, "subpopulation", None) is None:
                    continue

                # --- Preserve biological channel identity (one-time) ---
                if not hasattr(p, "_base_subpopulation"):
                    p._base_subpopulation = p.subpopulation


                # Optional hypothesis-based routing
                hypothesis_id = getattr(p, "hypothesis_id", None)

                routed_channel = self.hypothesis_router.route(
                    hypothesis_id=hypothesis_id,
                    default_channel=p._base_subpopulation,
                )

                # Override channel ONLY if router says so
                if routed_channel is not None:
                    p.subpopulation = routed_channel

                assemblies.append(p)

        if not assemblies:
            return

        external_gain = {}
        external_bias = {}

        if self.enable_context:
            for p in assemblies:
                external_gain[p.assembly_id] = self.context.get_gain(p.assembly_id)
                ch = getattr(p, "subpopulation", None) or "default"
                b = self.context.get_bias(p.assembly_id)
                if b is not None:
                    external_bias.setdefault(ch, []).append(float(b))

            for ch, vals in list(external_bias.items()):
                external_bias[ch] = sum(vals) / len(vals) if vals else 0.0

        self.competition_kernel.apply(
            assemblies,
            self.dt,
            external_gain=external_gain or None,
            external_bias=external_bias or None,
        )

        self._last_striatum_snapshot = {
            "winner": self.competition_kernel.last_winner_channel,
            "dominance": dict(self.competition_kernel.last_dominance_map),
            "instant": dict(self.competition_kernel.last_instantaneous_map),
            "routing": {
                p.assembly_id: p.subpopulation for p in assemblies
            },
            "time": self.time,
        }


        if self.enable_persistence:
            max_out = max(p.output() for p in assemblies)
            for p in assemblies:
                if p.output() >= max_out * 0.95:
                    self.bg_persistence.reinforce(p.assembly_id, amount=0.02)
            self.bg_persistence.step(self.dt)

    def _compute_gpi_relief(self) -> float:
        if not self.enable_gpi_disinhibition:
            return 1.0

        gpi = self.region_states.get("gpi")
        if not gpi:
            return 1.0

        outs = [
            float(p.output())
            for plist in gpi["populations"].values()
            for p in plist
        ]
        if not outs:
            return 1.0

        gpi_mean = sum(outs) / len(outs)
        relief = 1.0 - self.gpi_gain * gpi_mean
        return max(self.gpi_floor, min(1.0, relief))
    
    def _compute_recall_packet(self):
        """
        Collects recall-driven influence proposals.
        Execution-neutral. Pure packet construction.
        """
        try:
            from memory.replay_recall.pipeline import ReplayRecallPipeline
            from memory.influence_arbitration.influence_packet import InfluencePacket
        except ImportError:
            from memory.influence_arbitration.influence_packet import InfluencePacket
            return InfluencePacket(targets={})

        if not hasattr(self, "_recall_pipeline"):
            self._recall_pipeline = ReplayRecallPipeline()

        suggestions = self._recall_pipeline.query(runtime=self)

        # Convert suggestions → InfluencePacket
        targets = {}
        for s in suggestions:
            targets[s.target] = targets.get(s.target, 0.0) + float(s.magnitude)
            
        return InfluencePacket(targets=targets)

    def _evaluate_decision_latch(self, relief: float) -> None:
        if self._decision_fired:
            return

        snap = getattr(self, "_last_striatum_snapshot", None)
        if not snap:
            self._decision_counter = 0
            return

        dom = snap.get("dominance", {})
        if len(dom) < 2:
            self._decision_counter = 0
            return

        vals = sorted(dom.values(), reverse=True)
        delta = vals[0] - vals[1]

        # ------------------------------------------------------------
        # TEST-ONLY coincidence bias (decays automatically)
        # ------------------------------------------------------------
        if self._test_coincidence_enabled and self._test_coincidence_steps > 0:
            delta += self._test_delta_boost
            relief += self._test_relief_boost

            self._test_coincidence_steps -= 1
            if self._test_coincidence_steps <= 0:
                self._test_coincidence_enabled = False

# ------------------------------------------------------------
# Normal latch logic (unchanged)
# ------------------------------------------------------------


        if (
            delta >= self.DECISION_DOMINANCE_THRESHOLD
            and relief >= self.DECISION_RELIEF_THRESHOLD
        ):
            self._decision_counter += 1
        else:
            self._decision_counter = 0

        if self._decision_counter >= self._decision_sustain_required:
            self._decision_fired = True
            self._decision_state = {
                "time": self.time,
                "step": self.step_count,
                "winner": snap.get("winner"),
                "delta_dominance": delta,
                "relief": relief,
            }

            if self.enable_pfc_adapter:
                self.pfc_adapter.ingest_decision(
                    {
                        "commit": True,
                        "winner": snap.get("winner"),
                        "confidence": min(
                            1.0,
                            delta / max(self.DECISION_DOMINANCE_THRESHOLD, 1e-6),
                        ),
                    }
                )

            if self.enable_decision_bias:
                self.decision_bias.apply_decision(
                    winner=snap.get("winner"),
                    channels=list(dom.keys()),
                    strength=min(
                        1.0,
                        delta / max(self.DECISION_DOMINANCE_THRESHOLD, 1e-6),
                    ),
                    step=self.step_count,
                )

    def _propagate_connectivity(self, relief: float) -> None:
        fx_gain = (
            self.decision_fx.get_thalamic_gain_modifier()
            if self.enable_decision_fx and self._decision_state is not None
            else 1.0
        )

        for src_key, state in self.region_states.items():
            outputs = state.get("def", {}).get("outputs", [])
            if not outputs:
                continue

            src_pops = [p for plist in state["populations"].values() for p in plist]
            if not src_pops:
                continue

            src_drive = sum(p.output() for p in src_pops) / len(src_pops)

            for out in outputs:
                target_label = (
                    out.get("target")
                    or out.get("region")
                    or out.get("target_region")
                    or ""
                )
                tgt_key = self._resolve_region_key(target_label)
                if not tgt_key or tgt_key not in self.region_states:
                    continue

                strength = float(out.get("strength", 1.0))

                # Optional per-output population targeting
                target_pop = out.get("target_population") or out.get("population")

                # ---------------- Routing influence (gain-only, pre-BG) ----------------
                routing_gain = 1.0
                if hasattr(self, "routing_influence"):
                    gains = []
                    for p in src_pops:
                        hid = getattr(p, "hypothesis_id", None)
                        ch = getattr(p, "subpopulation", None)
                        g = self.routing_influence.gain_for(
                            assembly_id=p.assembly_id,
                            hypothesis_id=hid,
                            target_channel=ch,
                        )
                        gains.append(g)

                    if gains:
                        routing_gain = sum(gains) / len(gains)

                gain = routing_gain * (self._urgency_gain if self.enable_urgency else 1.0)

                if src_key.lower() == "gpi" and tgt_key.lower() == "md":
                    self._apply_input_to_region(
                        tgt_key,
                        src_drive * strength * relief * fx_gain * gain,
                        target_population=target_pop,
                    )
                else:
                    self._apply_input_to_region(
                        tgt_key,
                        src_drive * strength * gain,
                        target_population=target_pop,
                    )



    def _apply_input_to_region(
        self,
        region_key: str,
        amount: float,
        *,
        target_population: Optional[str] = None,
    ) -> None:
        region = self.region_states.get(region_key)
        if not region:
            return

        pops_map = region.get("populations", {}) or {}

        # If no target population specified, broadcast to all assemblies.
        if not target_population:
            for plist in pops_map.values():
                for p in plist:
                    p.input += amount
            return

        # Normalize label
        tp = str(target_population).strip()

        # Direct hit
        if tp in pops_map:
            for p in pops_map[tp]:
                p.input += amount
            return

        # Case-insensitive hit
        tp_lower = tp.lower()
        for k in pops_map.keys():
            if str(k).lower() == tp_lower:
                for p in pops_map[k]:
                    p.input += amount
                return

        # ------------------------------------------------------------
        # Alias shim for known "early-file" intent artifacts
        # (do NOT assume these exist everywhere)
        # ------------------------------------------------------------

        # Common: older configs say L5_PYRAMIDAL, runtime has L5_PYRAMIDAL_A/B
        if tp_lower == "l5_pyramidal":
            a = pops_map.get("L5_PYRAMIDAL_A")
            b = pops_map.get("L5_PYRAMIDAL_B")

            if a or b:
                if a:
                    for p in a:
                        p.input += amount
                if b:
                    for p in b:
                        p.input += amount
                return

        # If we get here, the target pop doesn't exist in this region.
        # We intentionally no-op (silent) to avoid destabilizing runtime.
        return

    # ============================================================
    # post-decision API
    # ============================================================

    def inject_decision_coincidence(
        self,
        *,
        delta_boost: float,
        relief_boost: float,
        steps: int,
    ) -> None:
        """
        TEST-ONLY.

        Temporarily biases decision coincidence variables so the
        latch may fire naturally.

        Does NOT:
        - set a winner
        - bypass latch logic
        - alter thresholds
        """
        self._test_coincidence_enabled = True
        self._test_delta_boost = float(delta_boost)
        self._test_relief_boost = float(relief_boost)
        self._test_coincidence_steps = int(steps)


    # ============================================================
    # Diagnostics
    # ============================================================

    def reset_hypothesis_routing(self) -> None:
        """
        Restore all assemblies to their original biological subpopulation
        assignments after hypothesis-based routing.
        """
        for p in self._all_pops:
            if hasattr(p, "_base_subpopulation"):
                p.subpopulation = p._base_subpopulation


    def snapshot_region_stats(self, region_key: str) -> Optional[Dict[str, Any]]:
        """
        Read-only diagnostic summary for a region.

        Mirrors the TCP `stats <region>` command.
        Safe for tests, probes, and notebooks.
        """
        rk = self._resolve_region_key(region_key) or region_key
        region = self.region_states.get(rk)
        if not region:
            return None

        acts: List[float] = []
        outs: List[float] = []

        for plist in region["populations"].values():
            for pop in plist:
                acts.append(float(getattr(pop, "activity", 0.0)))
                outs.append(float(pop.output()))

        if not acts:
            return {
                "region": region_key,
                "mass": 0.0,
                "mean": 0.0,
                "std": 0.0,
                "n": 0,
            }

        mean = sum(acts) / len(acts)
        var = sum((v - mean) ** 2 for v in acts) / len(acts)

        return {
            "region": region_key,
            "mass": sum(outs),
            "mean": mean,
            "std": var ** 0.5,
            "n": len(acts),
        }


    def snapshot_gate_state(self) -> Dict[str, Any]:
        """
        Read-only snapshot of GPi gate state and decision latch.

        Canonical source for tests and TCP inspection.
        """
        return {
            "time": self.time,
            "relief": self._last_gate_strength,
            "decision": self._decision_state,
        }


    def get_decision_state(self) -> Optional[Dict[str, Any]]:
        return self._decision_state

    def get_decision_bias(self) -> Dict[str, float]:
        return self.decision_bias.dump() if self.enable_decision_bias else {}

    def get_decision_fx_state(self) -> Dict[str, Any]:
        return self.decision_fx.dump() if self.enable_decision_fx else {}
    
    def snapshot_decision_fx(self) -> Dict[str, Any]:
        """
        Canonical Decision FX snapshot for TCP / tests.

        Returns a JSON-serializable dict with the *effect bundle* that would be
        applied downstream (thalamic_gain, region_gain, suppress_channels, lock_action).

        Read-only. Safe to call any time.
        """
        if not self.enable_decision_fx:
            return {
                "enabled": False,
                "bundle": None,
            }

        try:
            bundle = self.decision_fx.dump()
        except Exception as e:
            return {
                "enabled": True,
                "error": str(e),
                "bundle": None,
            }

        # Normalize: always return a dict with expected keys present (even if empty)
        out = {
            "enabled": True,
            "bundle": {
                "thalamic_gain": float(bundle.get("thalamic_gain", 1.0) or 1.0),
                "region_gain": dict(bundle.get("region_gain", {}) or {}),
                "suppress_channels": dict(bundle.get("suppress_channels", {}) or {}),
                "lock_action": bool(bundle.get("lock_action", False)),
            },
        }
        return out

    def get_control_state(self) -> Optional[ControlState]:
        return self._control_state