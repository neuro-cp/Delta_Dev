# Continuous Runtime Architecture

The continuous runtime controller is an in-process managed service loop. It owns lifecycle state, normalized event envelopes, wake policy, controller health, model residency metadata, active objectives, initiatives, and notification readiness. It reuses DELTA 1.2 live runtime, DELTA 1.5 evidence comparison, and DELTA 1.6 self-model instead of replacing them.

## Active Spine

The active runtime path is:

```text
UI Start Runtime
-> start_live_wikipedia_runtime
-> DELTA 1.2 LiveRuntimeState boot
-> ContinuousRuntimeController boot
-> operator/live events normalized into ContinuousEvent
-> bounded controller cycle
-> DELTA 1.6 background initiative/self-model sync
-> operator inquiry and promotion candidate surfaces
-> controller returns to IDLE
```

The controller is intentionally in-process. It does not create hidden threads,
daemons, external schedulers, or background services. The UI remains the
operator-controlled lifecycle boundary.

## Ownership

- `LiveRuntimeState` remains the lower-level cognitive event and journal runtime.
- `LiveWikipediaRuntimeSession` remains the live chat and Wikipedia bridge.
- `ContinuousRuntimeController` owns the service lifecycle, normalized events,
  wake mode, health, objectives, initiative queue, model-residency inventory,
  notification readiness, and shutdown state.
- `OperationalSelfModel` remains a derived snapshot. It is not the lifecycle
  authority.

## Safety

The controller may run deterministic local analysis and queue review items. It
may not call providers, retrieve arbitrary web pages, write memory, mutate the
repository, promote sandbox changes, commit, push, deploy, access secrets, or
change governance.
