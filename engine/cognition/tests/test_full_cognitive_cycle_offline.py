# engine/cognition/tests/test_full_cognitive_cycle_offline.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from loader.loader import NeuralFrameworkLoader
from engine.runtime import BrainRuntime

# Phase 6 cognition (offline)
from engine.cognition.hypothesis_registry import HypothesisRegistry as CogHypothesisRegistry
from engine.cognition.hypothesis_grounding import HypothesisGrounding
from engine.cognition.hypothesis_dynamics import HypothesisDynamics
from engine.cognition.hypothesis_competition import HypothesisCompetition
from engine.cognition.hypothesis_stabilization import HypothesisStabilization
from engine.cognition.hypothesis_bias import HypothesisBias


BASE_DIR = Path(__file__).resolve().parents[3]  # repo root


# ============================================================
# Minimal read-only adapter for numeric signals -> "assembly-like"
# ============================================================
@dataclass(frozen=True)
class _ObservedAssembly:
    """
    Offline, read-only observation wrapper.
    Implements the single method HypothesisGrounding needs: output().
    """
    assembly_id: str
    value: float

    def output(self) -> float:
        return float(self.value)

def _unwrap_replay_frame(frame: Any) -> List[Any]:
    """
    EpisodeReplay emits (Episode, [snapshots]).
    Return the list of snapshots.
    """
    if isinstance(frame, tuple) and len(frame) == 2:
        _, payload = frame
        if isinstance(payload, list):
            return payload
    return []


def _brain_compile(root: Path) -> Dict[str, Any]:
    loader = NeuralFrameworkLoader(root)
    loader.load_neuron_bases()
    loader.load_regions()
    loader.load_profiles()
    return loader.compile(
        expression_profile="minimal",
        state_profile="awake",
        compound_profile="experimental",
    )


def _attach_episode_observer(runtime: BrainRuntime) -> Tuple[Any, Any]:
    """
    Attach Phase-5 episodic observer (read-only), signature-safely.

    We pass only supported kwargs to EpisodeRuntimeHook.__init__ to handle
    minor repo variations without changing contracts.
    """
    import inspect

    from memory.episodic.episode_tracker import EpisodeTracker
    from memory.episodic.episode_trace import EpisodeTrace
    from memory.episodic.episode_boundary_policy import EpisodeBoundaryPolicy
    from memory.episodic.episode_runtime_hook import EpisodeRuntimeHook

    trace = EpisodeTrace()
    tracker = EpisodeTracker(trace=trace)
    policy = EpisodeBoundaryPolicy()

    sig = inspect.signature(EpisodeRuntimeHook.__init__)
    accepted = set(sig.parameters.keys())

    kwargs: Dict[str, Any] = {}
    if "tracker" in accepted:
        kwargs["tracker"] = tracker
    if "trace" in accepted:
        kwargs["trace"] = trace

    # Some snapshots accept policy/boundary_policy; others hardcode internally.
    if "policy" in accepted:
        kwargs["policy"] = policy
    elif "boundary_policy" in accepted:
        kwargs["boundary_policy"] = policy

    if not kwargs:
        raise TypeError(
            f"EpisodeRuntimeHook.__init__ has unsupported signature: {sig}. "
            "Expected at least one of: tracker, trace, policy/boundary_policy."
        )

    runtime.episode_hook = EpisodeRuntimeHook(**kwargs)
    return tracker, trace


def _episodes_from_tracker(tracker: Any) -> Sequence[Any]:
    eps = getattr(tracker, "episodes", None)
    if eps is None:
        raise AssertionError("EpisodeTracker has no .episodes property (contract mismatch)")
    return list(eps)


def _replay_episode(episodes: Sequence[Any], trace: Any) -> List[Any]:
    from memory.episodic.episode_replay import EpisodeReplay

    replay = EpisodeReplay(episodes=episodes, trace=trace)

    if hasattr(replay, "run"):
        return list(replay.run())
    if hasattr(replay, "replay"):
        return list(replay.replay())

    raise AssertionError("EpisodeReplay has neither .run() nor .replay() (contract mismatch)")


def _run_to_decision(runtime: BrainRuntime, *, warmup: int = 100, max_steps: int = 1400) -> Dict[str, Any]:
    """
    Drive runtime until a decision occurs.

    Uses:
    - lawful latch mechanics
    - runtime's TEST-ONLY coincidence injector (does not set winner)
    - a small striatal input pulse using canonical population IDs
    """
    for _ in range(warmup):
        runtime.step()

    sustain = int(getattr(runtime, "_decision_sustain_required", runtime.DECISION_SUSTAIN_STEPS))

    runtime.inject_decision_coincidence(
        delta_boost=runtime.DECISION_DOMINANCE_THRESHOLD,
        relief_boost=runtime.DECISION_RELIEF_THRESHOLD,
        steps=max(1, sustain),
    )

    def pulse() -> None:
        # Canonical IDs per your loader dump:
        runtime.inject_stimulus("striatum", "D1_MSN", magnitude=0.018)
        runtime.inject_stimulus("striatum", "D2_MSN", magnitude=0.012)

    for i in range(max_steps):
        if i < 10:
            pulse()
        runtime.step()

        d = runtime.get_decision_state()
        if d is not None:
            return d

    raise AssertionError("No decision occurred within max_steps")


# ============================================================
# Frame normalization (EpisodeReplay returns tuple frames here)
# ============================================================
def _normalize_frame(frame: Any) -> Any:
    """
    EpisodeReplay in this repo snapshot returns tuples.
    Common shapes: (step, snapshot) or (t, snapshot) or (meta, snapshot, ...).

    We treat the last element as the payload if it's a tuple.
    """
    if isinstance(frame, tuple) and len(frame) > 0:
        return frame[-1]
    return frame


# ============================================================
# Grounding extraction
# ============================================================
def _extract_observed_association_assemblies(frame: Any) -> List[Any]:
    """
    Best case: replay frame provides PopulationModel-like objects directly.
    """
    frame = _normalize_frame(frame)

    if isinstance(frame, dict):
        ac = frame.get("association_cortex") or frame.get("ASSOCIATION_CORTEX")
        if isinstance(ac, list) and ac:
            return ac

        assemblies = frame.get("assemblies")
        if isinstance(assemblies, list) and assemblies:
            return assemblies

    if hasattr(frame, "association_cortex"):
        ac = getattr(frame, "association_cortex")
        if isinstance(ac, list) and ac:
            return ac

    if hasattr(frame, "get"):
        try:
            ac = frame.get("association_cortex")
            if isinstance(ac, list) and ac:
                return ac
        except Exception:
            pass

    return []


def _extract_numeric_association_outputs(frame: Any) -> List[_ObservedAssembly]:
    """
    Schema-agnostic fallback.

    Recursively walk the replay payload and collect numeric leaves whose *path*
    indicates association_cortex.
    """
    import math

    frame = _normalize_frame(frame)

    def is_num(x: Any) -> bool:
        if isinstance(x, bool):
            return False
        if isinstance(x, (int, float)):
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return False
            return True
        return False

    def iter_children(o: Any) -> List[Tuple[str, Any]]:
        if isinstance(o, dict):
            return [(str(k), v) for k, v in o.items()]
        if isinstance(o, (list, tuple)):
            return [(f"[{i}]", v) for i, v in enumerate(o)]
        try:
            d = vars(o)
            if isinstance(d, dict):
                return [(str(k), v) for k, v in d.items()]
        except Exception:
            pass
        return []

    def path_has_ac(path: List[str]) -> bool:
        p = "/".join(path).lower()
        return ("association_cortex" in p) or ("association_cortex:" in p)

    out: List[_ObservedAssembly] = []
    seen: set[Tuple[str, float]] = set()

    stack: List[Tuple[Any, List[str]]] = [(frame, ["frame"])]
    visited_ids: set[int] = set()

    while stack:
        node, path = stack.pop()
        nid = id(node)

        if nid in visited_ids:
            continue
        visited_ids.add(nid)

        if is_num(node):
            if path_has_ac(path):
                aid = "/".join(path)
                key = (aid, float(node))
                if key not in seen:
                    seen.add(key)
                    out.append(_ObservedAssembly(assembly_id=aid, value=float(node)))
            continue

        if isinstance(node, dict):
            for k, v in node.items():
                ks = str(k)
                if ks.lower().startswith("association_cortex:") and is_num(v):
                    key = (ks, float(v))
                    if key not in seen:
                        seen.add(key)
                        out.append(_ObservedAssembly(assembly_id=ks, value=float(v)))

        for k, v in iter_children(node):
            stack.append((v, path + [k]))

    return out


def _support_to_activation(h: Any, *, max_support: float) -> float:
    """
    TEST-ONLY glue: monotone bounded support->activation mapping.
    """
    s = float(getattr(h, "support", 0.0))
    if max_support <= 0:
        return 0.0
    a = s / max_support
    if a < 0.0:
        return 0.0
    if a > 1.0:
        return 1.0
    return a


# ============================================================
# Integration test
# ============================================================
def test_full_cognitive_cycle_offline() -> None:
    brain = _brain_compile(BASE_DIR)
    rt = BrainRuntime(brain, dt=0.01)

    tracker, trace = _attach_episode_observer(rt)

    decision = _run_to_decision(rt, warmup=100, max_steps=1400)
    assert decision.get("winner") is not None, "Decision fired but has no winner"

    episodes = _episodes_from_tracker(tracker)
    assert len(episodes) >= 1, "No episodes captured by EpisodeTracker"

    frames = _replay_episode(episodes, trace)
    assert len(frames) > 0, "EpisodeReplay produced no frames"

    reg = CogHypothesisRegistry()

    h0 = reg.create(hypothesis_id="H0", created_step=0)
    h1 = reg.create(hypothesis_id="H1", created_step=0)

    # TEST-ONLY: allow grounding to sustain, not create, hypotheses
    h0.activation = 0.08
    h1.activation = 0.08


    grounding = HypothesisGrounding(support_gain=1.0, max_support=10.0)
    dynamics = HypothesisDynamics(decay_rate=0.01)
    competition = HypothesisCompetition(competition_gain=0.05)
    stabilizer = HypothesisStabilization(activation_threshold=0.10, sustain_steps=5)
    biaser = HypothesisBias(bias_gain=0.05, max_bias=0.2)

    stabilized_ids: set[str] = set()

    for _, raw in enumerate(frames):
        reg.tick()

        snapshots = _unwrap_replay_frame(raw)

        for snap in snapshots:
            observed = _extract_observed_association_assemblies(snap)
            if not observed:
                observed = _extract_numeric_association_outputs(snap)

            if not observed:
                continue  # skip empty snapshots safely

            grounding.step(hypotheses=reg.all(), observed_assemblies=observed)

            for h in reg.all():
                if not h.active:
                    continue

                # Incremental activation update (persistence-aware)
                delta = _support_to_activation(h, max_support=grounding.max_support)
                h.activation = min(1.0, h.activation + delta)

            dynamics.step(reg.all())
            competition.step(reg.all())

            events = stabilizer.step(reg.all())
            for e in events:
                if e.get("event") == "hypothesis_stabilized":
                    stabilized_ids.add(str(e.get("hypothesis_id")))

            if stabilized_ids:
                break  # exit snapshot loop

        if stabilized_ids:
            break  # exit frame loop

    assert stabilized_ids, "No hypothesis stabilized during replay"

    stabilized = [
        h for h in reg.all()
        if h.hypothesis_id in stabilized_ids and h.active
    ]
    assert stabilized, "Stabilization events occurred but stabilized hypotheses are not active"

    bias = biaser.compute_bias(stabilized_hypotheses=stabilized)
    assert bias, "Expected non-empty bias dict from stabilized hypotheses"

    for hid, val in bias.items():
        assert hid in stabilized_ids
        assert 0.0 < float(val) <= biaser.max_bias
