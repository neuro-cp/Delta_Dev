# Original DELTA Runtime Path Trace

Generated: `2026-07-02`

Source root: `G:\Delta_DevV0`

Start point: `G:\Delta_DevV0\engine\runtime.py`

## Summary

I traced outward from the original `BrainRuntime` rather than doing a broad file
inventory. My read: the original runtime itself should not be transplanted into
the current repo. It is a dense dynamical core with direct stimulation,
competition, gating, persistence, recall influence, and optional execution
hooks.

The adoptable value is in the boundary objects and read-only hooks around it:

1. episodic observation / boundary / trace / replay
2. hypothesis trace and report-only hypothesis processing
3. execution authorization gate concepts
4. attention and working-memory runtime snapshots
5. value/urgency traces as future confidence/volatility inspiration

The strongest near-term adoption target is the episodic/replay path because it
fits the current V1.4D bridge:

`AnswerTrace -> FeedbackCaptureRecord -> ReplayReviewMarker -> future replay`

## Runtime.py Shape

`engine/runtime.py` defines `BrainRuntime`, the original ground-truth dynamical
runtime. It owns:

- region state
- population models
- stimulus queue
- competition and basal-ganglia persistence
- context, salience, decision bias, value, urgency
- working-state adapter
- decision latch
- hypothesis routing/proposal/pressure
- execution gate
- recall runtime bridge
- observation hook
- episodic boundary hook

It should be treated as an architectural reference, not copied.

## Direct Runtime Spokes Traced

### Execution Gate Path

Files traced:

- `engine/execution/execution_gate.py`
- `engine/execution/execution_state.py`
- `engine/execution/execution_target.py`
- `memory/recall_runtime_bridge/recall_runtime_adapter.py`
- `memory/recall_runtime_bridge/recall_runtime_result.py`
- `memory/recall_runtime_bridge/recall_runtime_policy.py`

Finding:

- `ExecutionGate` itself is conceptually useful: it fail-closes when disabled
  and returns identity values when a target is not allowed.
- `ExecutionState(enabled=False)` is aligned with current DELTA safety.
- `ExecutionTarget` is a useful enum concept for future AEM-style authorization.
- `RecallRuntimeAdapter` is risky as code because it applies influence packets
  into runtime through the gate.
- `RecallRuntimePolicy.ENABLE_RECALL_EXECUTION = True` is not safe for current
  V1.4 defaults.

Adoption recommendation:

- Do not copy the recall bridge.
- Reuse the idea of identity-preserving execution gates later.
- Translate into a future dormant authorization packet / AEM gate scaffold.

Status for current roadmap:

`defer until execution authorization design`

### Observation and Episodic Boundary Path

Files traced:

- `engine/observation/observation_runtime_hook.py`
- `engine/observation/observation_engine.py`
- `engine/observation/observation_event.py`
- `memory/episodic/episode_trace.py`
- `memory/episodic/episode_tracker.py`
- `memory/episodic/episode_runtime_hook.py`
- `memory/episodic/episode_structure.py`
- `memory/episodic/episode_replay.py`
- `memory/episodic_boundary/boundary_adapter.py`

Finding:

This is the best adoption path so far.

The old code already has the right philosophy:

- read-only runtime hook
- immutable observation events
- append-only episodic trace
- passive episode tracker
- boundary adapter emits declarative events
- replay aligns timelines offline
- no runtime mutation
- no learning
- no authority

This maps cleanly to current DELTA V1.4:

- `ObservationEvent` resembles future answer/episode facts.
- `EpisodeTraceRecord` maps to future trace records.
- `EpisodeReplay` maps strongly to sleep/replay design.
- `BoundaryAdapter` maps to a future replay-boundary classifier.

Adoption recommendation:

- Use these files as the starting reference for `Runtime V1.4E - Sleep/Replay
  Consolidation Design`.
- Do not copy names blindly; adapt into current `AnswerTrace`,
  `FeedbackCaptureRecord`, and `ReplayReviewMarker` style.
- Preserve the non-responsibility language. It is excellent and should become
  part of DELTA's implementation pattern.

Status for current roadmap:

`high-confidence conceptual adoption`

### Attention / Working Memory Snapshot Path

Files traced:

- `memory/attention/attention_runtime_hook.py`
- `memory/working_memory/working_memory_runtime_hook.py`

Finding:

These are read-only snapshot hooks. They do not mutate runtime and distinguish
computed bias from applied gain.

Adoption recommendation:

- Useful as style references for future Runtime V1.4 reports.
- Do not wire them into current activation/attention behavior.
- Could inform future answer-trace enrichment: what was active, what was
  biased, what remained observational only.

Status for current roadmap:

`adapt as report-only diagnostics later`

### Hypothesis Routing Path

Files traced:

- `engine/routing/hypothesis_registry.py`
- `engine/routing/hypothesis_router.py`
- `engine/routing/hypothesis_generator.py`
- `engine/routing/hypothesis_pressure.py`
- `engine/routing/routing_influence.py`
- `engine/cognition/hypothesis/hypothesis.py`
- `engine/cognition/hypothesis/hypothesis_competition.py`
- `engine/cognition/hypothesis/hypothesis_grounding.py`
- `engine/cognition/hypothesis/hypothesis_stabilization.py`
- `engine/cognition/hypothesis/hypothesis_registry.py`
- `engine/cognition/hypothesis/offline/hypothesis_trace.py`
- `engine/cognition/hypothesis/offline/hypothesis_runner.py`

Finding:

There are two different hypothesis layers:

1. Runtime routing hypothesis utilities that can affect channels/gains.
2. Offline hypothesis cognition utilities that are much safer.

The safer layer is the offline one:

- `Hypothesis`
- `HypothesisTrace`
- `HypothesisStabilization`
- `HypothesisRunner`

These preserve a useful pattern:

- hypotheses are explicit objects
- trace records are forensic and append-only
- runner is offline only
- no runtime authority
- no memory writes
- deterministic step order

Risk:

- `HypothesisCompetition` mutates hypothesis objects in place.
- `HypothesisRegistry.remove()` deletes hypotheses.
- `RoutingInfluence` can affect runtime gain.

Adoption recommendation:

- Do not adopt runtime routing influence yet.
- Adapt the offline hypothesis trace/runner pattern as a future report-only
  `hypothesis arbitration` design.
- If copied later, make hypothesis state immutable or explicitly trace-mutated
  through envelopes.

Status for current roadmap:

`medium-confidence report-only conceptual adoption`

## Strongest Immediate Lesson

The original DELTA already had a discipline that matches the current direction:

> observation first, trace second, replay offline, mutation later or never.

That is exactly the architecture we should preserve.

## Recommended Next Step

For V1.4E, do not invent sleep/replay from scratch. Use the original episodic
path as source material:

1. `ObservationEvent`
2. `EpisodeTraceRecord`
3. `EpisodeTracker`
4. `EpisodeReplay`
5. `BoundaryAdapter`

Translate them into current repo terms:

1. `AnswerTrace`
2. `FeedbackCaptureRecord`
3. `ReplayReviewMarker`
4. future `ReplayConsolidationReview`
5. future `ReplayBoundaryDecision`

## My Opinion

Yes, original DELTA can save time, but not by copying `engine/runtime.py`.

The original runtime is too entangled with the older dynamical simulation to
drop into the current Model B/HYB1 runtime. The surrounding read-only hooks,
trace records, replay alignment utilities, and offline hypothesis tooling are
where the real reusable value is.

The best compromise is:

- keep current Runtime V1.3/V1.4 as the safe cognition kernel;
- mine original DELTA for naming, boundaries, trace objects, and invariants;
- adopt episodic/replay concepts next;
- keep execution, recall influence, routing gain, live pruning, and training
  deferred.

## Continuation Checkpoint

- `trace_started_from`: `G:\Delta_DevV0\engine\runtime.py`
- `do_not_copy_runtime_py`: `True`
- `best_adoption_path`: `episodic observation -> boundary -> trace -> replay`
- `second_adoption_path`: `offline hypothesis trace/arbitration`
- `defer`: `execution gate activation, recall runtime bridge, routing influence`
- `recommended_next_phase`: `Runtime V1.4E - Sleep/Replay Consolidation Design`
