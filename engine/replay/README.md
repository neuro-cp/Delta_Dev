# Replay Subsystem (Offline, Non-Authoritative)

This package defines the **replay scheduling layer** of the system.

Replay is strictly:
- Offline
- Deterministic
- Read-only with respect to runtime
- Non-persistent
- Non-semantic

## What Replay Is

Replay is the *re-exposure* of episodic data to downstream cognition.
It does **not** imply learning, consolidation, promotion, or memory mutation.

Replay answers only one question:

> Which slices of the past may be revisited?

## What Replay Is Not

Replay does NOT:
- Modify runtime behavior
- Influence decisions
- Shape salience
- Persist state across runs
- Encode meaning
- Perform consolidation

## Architectural Position

Replay sits between:

Episodic Memory → Cognition (offline)

It is blind to:
- REM / NREM semantics
- Time-of-day meaning
- Learning outcomes
- Semantic importance

Replay scheduling responds to **ReplayRequests**, not fixed circadian time.

## Key Invariant

Replay is exposure without consequence.  
Consolidation is consequence without ambiguity.

If replay produces durable change, this contract has been violated.
