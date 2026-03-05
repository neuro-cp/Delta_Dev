# Semantic Boundary Contract

Status: DESIGN-ONLY (No runtime wiring permitted)

This document defines the hard boundary between the
**pre-semantic substrate** and any future **semantic layer**.

The purpose of this contract is to prevent semantic interpretation
from acquiring authority, control, or persistence prematurely.

---

## 1. What Semantics IS

Semantics is an **interpretive layer** that:

- assigns *meaning labels* to observed cognitive patterns
- proposes *descriptions*, not actions
- operates **offline only**
- is always reconstructible from inspection artifacts

Semantics exists to help a human (or later system)
*understand what cognition might mean*.

---

## 2. What Semantics MAY READ

Semantics MAY read:

- Inspection artifacts
  - HypothesisTimeline
  - HypothesisEpisodeStats
  - DiffReport
  - ReplayExecutionReport
- Episodic metadata (read-only)
- Consolidation summaries (descriptive only)

Semantics MAY NOT read:

- Runtime state
- Live salience fields
- Control signals
- Decision latch state
- Any mutable memory structures

---

## 3. What Semantics MAY PRODUCE

Semantics MAY emit:

- SemanticAnnotation (descriptive)
- PromotionCandidate (proposal only)
- Human-readable summaries
- Offline reports

All semantic outputs must be:

- immutable
- discardable
- reproducible
- explicitly marked as *non-authoritative*

---

## 4. What Semantics MAY NOT DO (Hard Prohibitions)

Semantics MAY NOT:

- trigger replay
- initiate sleep
- modify salience
- bias routing or decision
- persist state across runs
- learn or optimize parameters
- create or close episodes
- mutate memory schemas
- execute during runtime steps

Violation of any of the above requires
a formal architectural reopening.

---

## 5. Time Semantics Lives In

Semantics exists strictly in **retrospective time**:

Runtime → Episodic → Replay → Cognition → Inspection → Semantics

There is no backward edge.

---

## 6. Design Intent

Semantics must remain:

- slower than control
- weaker than cognition
- less trusted than inspection

Meaning must never outrun evidence.

---

## 7. Lock Condition

This contract is binding until:

- semantics are proven safe in isolation
- a promotion mechanism is specified
- memory lifecycle rules are defined
- regression guards exist

Until then:

**Semantics is advisory only.**
