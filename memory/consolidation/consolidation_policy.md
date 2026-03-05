# Consolidation Policy — v0

Status: ACTIVE  
Phase: 8 (Offline Consolidation)  
Authority: NONE  
Scope: Episodic → Semantic transformation (read-only)

---

## Purpose

This policy defines what *consolidation* is allowed to do
and, more importantly, what it is forbidden from doing.

Consolidation transforms **episodes** into **semantic records**.

It does not act.
It does not decide.
It does not influence runtime behavior.

---

## Core Principle

Consolidation is **archival compression**, not learning.

It summarizes what happened.
It does not change what happens next.

---

## Inputs

Consolidation may read:

- Closed `Episode` objects
- `EpisodeTrace` history
- Derived replay views (`EpisodeReplay`)

Consolidation MUST NOT read:

- Runtime state
- Population activity
- Context, salience, bias, or value
- Control or decision latch internals

---

## Outputs

Consolidation may produce:

- Immutable semantic records
- Aggregated statistics
- Descriptive tags
- Offline summaries

All outputs MUST be:

- Deterministic
- Immutable
- Serializable
- Safe to discard and recompute

---

## Explicit Prohibitions

Consolidation MUST NEVER:

- Modify episodes or traces
- Trigger resets
- Inject gain, bias, or salience
- Influence decision-making
- Create authority or intent
- Execute during runtime steps
- Depend on timing, urgency, or value signals

If consolidation output can change runtime behavior,
it violates this policy.

---

## Temporal Separation

Consolidation is **offline**.

It may run:

- After episodes close
- Between sessions
- In notebooks
- In background analysis tools

It MUST NOT run:

- Inside `BrainRuntime.step`
- Inside hooks
- Inside decision or control paths

---

## Identity & Ownership

Consolidation records:

- Do NOT replace episodes
- Do NOT overwrite memory
- Do NOT establish goals
- Do NOT persist executive state

They are *references*, not *beliefs*.

---

## Versioning

All consolidation logic must declare:

- Policy version
- Record schema version

Breaking changes require:
- New policy version
- New tests
- Explicit migration logic (offline only)

---

## Default Behavior (v0)

- Only closed episodes are consolidated
- Active episodes are ignored
- No consolidation output is consumed by runtime

---

## Rationale

Biological consolidation occurs during sleep and rest.
It is decoupled from action and decision.

This policy enforces that separation.

---

## Future Extensions (Non-Binding)

Possible future additions:

- Replay-weighted summaries
- Cross-episode clustering
- Schema induction
- Episodic → semantic promotion

All extensions must remain:
- Offline
- Read-only
- Non-authoritative

---

End of policy.
