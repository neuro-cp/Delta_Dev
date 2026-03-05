# Working State Reset Policy — v0

Status: DESIGN-ONLY  
Phase: 6B (Reset Policy)  
Applies to: PFC Working State (PFCAdapter)  
Authority: NONE (authorization-only)

---

## Purpose

This policy defines constraints under which **working state MAY be authorized
to disengage or attenuate across episode boundaries**.

Working state is adjacent to executive authority.
Therefore, resets are extremely constrained.

This document does NOT implement behavior.
This document does NOT alter working state dynamics.
This document only defines future permissions and prohibitions.

---

## Definitions

- **Working State**: Post-decision, executive persistence maintained by PFCAdapter.
- **Episode Boundary**: A closed Episode recorded by episodic memory.
- **Reset**: Disengagement, forced decay, or suppression of working state.
- **Authorization**: Permission only; never execution.

---

## Eligibility

Working state has been declared `ELIGIBLE` for episode-aware reset.

Eligibility does NOT imply default reset.

---

## Allowed Inputs (Read-Only)

A working state reset policy MAY observe:

- Episode.closed == True
- Episode.has_decision()
- Episode.confidence (if present)
- ControlState flags (fatigue, saturation)
- Time since decision commit
- Time since episode boundary

A working state reset policy MUST NOT observe:

- Striatal dominance values
- Gate relief
- Latch counters
- Population-level activity
- Salience fields
- Hypothesis routing

---

## Allowed Actions (Authorization Only)

If authorized, a working state reset MAY:

- Permit **graceful disengagement** (natural decay acceleration)
- Mark working state as “eligible for release”
- Allow control policy to release authority

A working state reset MUST NOT:

- Immediately disengage working state
- Cancel an active commitment
- Trigger a new decision
- Alter decision confidence
- Inject or suppress gain directly

---

## Forbidden Actions (Hard Invariants)

A working state reset policy MUST NEVER:

- Disengage working state on episode close alone
- Operate while decision latch is active
- Operate during post-commit control hold
- Override ControlPolicy decisions
- Cause re-deliberation implicitly
- Affect persistence, salience, or context directly

---

## Default Behavior (v0)

Under this version:

- Episode boundaries DO NOT affect working state
- Authorization always returns FALSE
- Working state behavior remains identical to Phase 4

---

## Rationale

Biological analogy:
Working memory persists across tasks until explicitly released.
Task boundaries do not imply loss of executive intent.

Premature working state resets risk:
- Thrashing between commitments
- Loss of temporal coherence
- Hidden re-decision events

---

## Future Revisions

Possible future allowances:
- Release eligibility after sustained low-confidence episodes
- Fatigue-mediated disengagement windows
- Episodic markers for executive handoff

All future revisions require:
- New version
- Explicit tests
- Proof of non-interference with decision latch and control

---
