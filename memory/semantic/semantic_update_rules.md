# Semantic Memory Update Rules — v0

Status: DRAFT  
Phase: 6B (Semantic Update & Maintenance)  
Authority: NONE  
Depends On:
- semantic_policy.md
- semantic_schema.md
- episodic consolidation (Phase 5B)

---

## Purpose

This document defines **how semantic memory may be created, updated, decayed, or retired**.

These rules govern *when* and *under what conditions* semantic records change.

This document does **not** define implementation.
It defines **permission and constraint**.

---

## Core Principle

Semantic memory changes **slowly**, **conservatively**, and **offline**.

Semantic updates reflect *persistent regularities*,
not transient events.

---

## Eligibility for Semantic Promotion

A pattern MAY be promoted to semantic memory only if:

1. It is observed across **multiple closed episodes**
2. It survives consolidation replay without mutation
3. It meets minimum evidence thresholds
4. It is stable across time, not burst-driven

### Minimum Requirements (v0 defaults)

- Minimum contributing episodes: **N ≥ 5**
- Minimum observation window: **non-trivial span**
- No single episode contributes more than one vote

Single-episode semantics are **explicitly forbidden**.

---

## Promotion Sources

Semantic promotion MAY draw from:

- ConsolidationRecord aggregates
- EpisodeReplay summaries
- Offline batch statistics

Semantic promotion MUST NOT draw from:

- Runtime state
- Active episodes
- Decision latch events
- Salience, value, or urgency signals

---

## Promotion Granularity

Semantic records are **coarse**.

Promotion MUST favor:

- Frequencies over instances
- Distributions over points
- Ranges over exact values

If a record can be traced to a specific moment,
it is **episodic**, not semantic.

---

## Update Cadence

Semantic updates occur only during **explicit offline phases**.

Allowed execution contexts:

- Post-session batch runs
- Idle / sleep phases
- Manual analysis passes

Forbidden contexts:

- During `BrainRuntime.step`
- During active episodes
- During decision evaluation
- Inside hooks or callbacks

Semantic memory MUST NOT update continuously.

---

## Update Operations (Allowed)

Semantic memory MAY perform the following operations:

### Add
- Introduce a new SemanticRecord
- Only when promotion criteria are met

### Strengthen
- Increase support metrics
- Narrow confidence intervals
- Extend temporal scope

### Weaken
- Reduce support due to non-observation
- Increase variance
- Apply decay

### Retire
- Mark records inactive
- Preserve provenance
- Do not delete immediately

---

## Update Operations (Forbidden)

Semantic memory MUST NEVER:

- Overwrite episodic memory
- Rewrite history
- Merge semantics with conflicting provenance
- Collapse dissimilar patterns prematurely
- Auto-delete without decay
- Perform credit assignment

---

## Decay Rules

Semantic memory decays **slowly**.

Decay MAY be based on:

- Time since last observation
- Declining support
- Increased variance

Decay MUST NOT:

- Be abrupt
- Be triggered by a single absence
- Depend on runtime urgency or value

Decay is **graceful forgetting**, not punishment.

---

## Conflict Resolution

If multiple semantic records conflict:

- Both may coexist
- Resolution is deferred
- Additional evidence is required

Semantic memory does not “choose winners.”

---

## Stability Bias

Semantic memory is biased toward **persistence**.

Once promoted, records should:

- Require substantial counter-evidence to weaken
- Survive short-term noise
- Favor historical consistency

This bias prevents semantic thrashing.

---

## Versioning & Migration

All semantic updates MUST record:

- Schema version
- Policy version
- Update timestamp (offline time)

Breaking changes require:

- New schema version
- Offline migration
- Validation tests

---

## Auditability

Semantic updates MUST be:

- Replayable
- Explainable
- Traceable to source episodes

If a semantic record cannot explain its provenance,
it must not exist.

---

## Explicit Prohibitions

Semantic update logic MUST NEVER:

- Influence decisions
- Bias salience or value
- Trigger learning during runtime
- Modify control state
- Act as a policy engine

Semantic memory remains **non-authoritative**.

---

## Invariants

At all times:

- Semantic memory is offline
- Semantic memory is advisory
- Semantic memory is slow
- Semantic memory is reversible
- Semantic memory is subordinate to episodic truth

Violation of any invariant is a system error.

---

## Phase Boundary

Completion of Phase 6B authorizes:

- Implementation of passive semantic containers
- Offline semantic builders
- Non-runtime semantic storage

It does NOT authorize:

- Runtime integration
- Action biasing
- Learning hooks

Those require a future phase.

---

End of rules.
