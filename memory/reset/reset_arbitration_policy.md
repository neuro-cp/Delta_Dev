# Reset Arbitration Policy — v0

Status: DESIGN-ONLY  
Phase: 6C (Reset Arbitration)  
Authority: NONE  
Scope: Cross-subsystem reset coordination

---

## Purpose

This policy defines how multiple reset-eligible subsystems
are coordinated without creating cascading resets,
hidden authority transfer, or implicit re-decision.

This document authorizes NOTHING.
This document executes NOTHING.

It defines ordering, priority, and prohibitions only.

---

## Core Principle

Reset eligibility ≠ reset permission  
Reset permission ≠ reset execution

All reset signals are advisory.
All execution remains elsewhere.

---

## Reset-Eligible Subsystems (Observed Only)

The following subsystems may emit **reset eligibility signals**:

- Episodic Memory (episode boundary)
- Context Memory (trace decay or exhaustion)
- Working State (post-commit persistence)
- Salience Field (decay exhaustion)

The following subsystems are NOT eligible:

- Decision Latch
- Competition Kernel
- GPi Gate
- Value System
- Urgency System
- Hypothesis Routing

These are hard exclusions.

---

## Arbitration Ordering (Fixed)

Eligibility signals MUST be evaluated in this order:

1. Decision State (GUARD)
2. Control State (GUARD)
3. Working State (EXECUTIVE)
4. Context Memory
5. Salience Field
6. Episodic Memory

Higher layers MAY veto lower layers.
Lower layers MUST NOT override higher layers.

---

## Guard Layers (Non-Negotiable)

### Decision State Guard

If decision latch is active:
- ALL reset authorization returns FALSE
- No subsystem may proceed

### Control State Guard

If ControlState indicates:
- committed == True
- suppress_alternatives == True
- working_state_active == True

Then:
- No reset authorization may be granted

---

## Arbitration Rules

- Only ONE reset eligibility may be authorized per episode boundary
- Authorization does NOT imply execution
- Authorization may expire if not consumed
- Authorization may be revoked by guard layers at any time

---

## Forbidden Patterns

Reset arbitration MUST NEVER:

- Trigger multiple resets in one step
- Cascade resets across subsystems
- Back-propagate resets upward
- Create implicit task boundaries
- Cause re-deliberation
- Modify salience, gain, or bias directly

---

## Default Behavior (v0)

Under this version:

- All reset authorization returns FALSE
- Arbitration performs no actions
- System behavior is identical to Phase 6

---

## Rationale

Biological systems do not globally reset.
They release selectively, conservatively, and late.

Arbitration prevents:
- Reset storms
- Executive thrashing
- Authority leaks
- Temporal incoherence

---

## Future Extensions

Possible future additions:
- Time-based arbitration windows
- Fatigue-weighted eligibility
- Explicit executive handoff markers

All extensions require:
- New version
- Dedicated tests
- Proof of non-interference with decision latch

---
