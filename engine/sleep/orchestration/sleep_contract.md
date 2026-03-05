# Sleep / Replay Orchestration Contract (v1)

## Purpose

This layer determines **when** and **how** offline replay may occur.
It is a policy and scheduling layer only.

It does NOT execute replay.
It does NOT influence runtime behavior directly.
It does NOT interpret cognition.

---

## Orchestration MAY:

- Observe inspection artifacts (diff summaries, counts, timestamps)
- Observe replay history metadata (counts, last replay step)
- Accept external or internal sleep requests
- Select a sleep profile
- Allocate a replay budget
- Emit an auditable SleepDecision

---

## Orchestration MAY NOT:

- Execute replay
- Modify runtime state
- Modify episodic memory
- Modify cognition or hypotheses
- Persist learning or semantics
- Trigger replay in the same timestep as action

---

## Temporal Guarantees

- All sleep decisions apply **strictly after** runtime execution
- Replay execution occurs **offline only**
- No orchestration decision may block or delay runtime steps

---

## Architectural Invariant

Removing the entire sleep/orchestration layer MUST NOT
change runtime behavior.

---

## Status

LOCKED unless explicitly reopened by architectural review.
