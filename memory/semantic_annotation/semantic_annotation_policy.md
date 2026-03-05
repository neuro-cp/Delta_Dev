# Semantic → Episodic Annotation Policy — v0

Status: DRAFT  
Phase: 8A (Offline Semantic Annotation)  
Authority: NONE  

---

## Purpose

This policy governs how semantic knowledge may annotate episodic memory.

Annotations are descriptive labels applied to past episodes
for inspection, analysis, and future offline learning.

Annotations do NOT influence behavior.

---

## Core Principle

Annotation is commentary, not control.

It describes what an episode resembles.
It does not alter what the system does next.

---

## Allowed Inputs

Annotation may read:

- Closed Episode objects
- EpisodeReplay views
- SemanticRegistry
- SemanticQueryInterface (read-only)

Annotation MUST NOT read:

- Runtime state
- Live control signals
- Salience, value, urgency
- Decision latch internals

---

## Allowed Outputs

Annotation may produce:

- Episode tags
- Episode notes
- Descriptive labels
- Confidence-free descriptors

All outputs MUST be:

- Immutable
- Deterministic
- Additive
- Removable

---

## Explicit Prohibitions

Annotation MUST NEVER:

- Modify episode structure
- Modify semantic records
- Trigger learning
- Affect future decision logic
- Persist authority
- Create preferences or rankings

Annotations are metadata only.

---

## Temporal Constraints

Annotation runs:

- During replay
- Offline
- After episode closure

Annotation MUST NOT run:

- During runtime execution
- During decision making
- During consolidation

---

## Directionality


No reverse flow is permitted.

---

## Audit Invariant

Removing all annotations MUST:

- Leave runtime behavior unchanged
- Leave decision statistics unchanged
- Leave consolidation unchanged

If not, this policy is violated.

---

## Phase Boundary

Completion of Phase 8A authorizes:

- Annotation engines
- Annotation tests
- Offline inspection tooling

It does NOT authorize:

- Learning
- Runtime feedback
- Semantic-driven bias

---

End of policy.
