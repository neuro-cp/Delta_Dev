# Context Reset Policy — v0

Status: DESIGN-ONLY  
Phase: 6B (Reset Policy)  
Applies to: RuntimeContext  
Authority: NONE (authorization-only)

---

## Purpose

This policy defines the conditions under which **context state MAY be authorized
for reset or attenuation across episode boundaries**.

This document does NOT implement behavior.
This document does NOT alter runtime dynamics.
This document only defines allowed future actions.

---

## Definitions

- **Context**: Gain- and bias-only situational modulation stored in RuntimeContext.
- **Episode Boundary**: A closed Episode as recorded by Episodic Memory.
- **Reset**: Any operation that reduces, clears, or attenuates context state.
- **Authorization**: Permission for a reset to occur, not execution.

---

## Eligibility

Context has been declared `ELIGIBLE` for episode-aware reset.
This policy governs IF and WHEN such reset could be permitted.

No reset may occur without satisfying this policy.

---

## Allowed Inputs (Read-Only)

A Context reset policy MAY observe:

- Episode.closed == True
- Episode.duration_steps
- Episode.has_decision()
- Episode.confidence (if present)
- ControlState flags (fatigue, saturation)
- Time since last episode boundary

A Context reset policy MUST NOT observe:

- Population activity directly
- Dominance deltas
- Gate relief
- Salience fields
- Hypothesis routing
- Raw neural outputs

---

## Allowed Actions (Authorization Only)

If authorized, a Context reset MAY:

- Apply a **multiplicative attenuation** to existing gains
- Increase decay rate temporarily
- Mark context state as “stale” for downstream systems

A Context reset MUST NOT:

- Inject new gain
- Flip bias polarity
- Introduce asymmetry
- Trigger learning
- Trigger decisions
- Trigger working state disengagement

---

## Forbidden Actions (Hard Invariants)

A Context reset policy MUST NEVER:

- Clear context immediately on episode close
- Perform a hard reset without a decision-bearing episode
- Operate during an active decision latch
- Operate during post-commit control hold
- Affect persistence or salience
- Influence striatal competition
- Modify latch thresholds or counters

---

## Default Behavior (v0)

Under this version:

- Episode boundaries DO NOT cause context reset
- Authorization always returns FALSE
- Context behavior is unchanged from Phase 5

This policy exists to define constraints, not behavior.

---

## Rationale

Biological analogy:
Context resembles situational bias, not task memory.
It should decay naturally and conservatively.

Premature resets risk:
- Task fragmentation
- Spurious novelty
- Instability across deliberation cycles

---

## Future Revisions

Future versions may allow:
- Soft attenuation after low-confidence episodes
- Partial decay boost under sustained fatigue
- Context snapshotting into episodic memory

All future changes require:
- New version number
- Explicit tests
- Proof of non-interference with decision core

---
