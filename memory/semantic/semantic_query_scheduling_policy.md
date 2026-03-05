# Semantic Query Scheduling Policy — v0

Status: DRAFT  
Phase: 7C (Semantic Query Timing & Eligibility)  
Authority: NONE  
Depends On:
- semantic_query_policy.md
- semantic_query_interface.py

---

## Purpose

This policy defines **when semantic memory may be queried**.

It exists to prevent semantic knowledge from influencing
decision-making through timing rather than content.

---

## Core Principle

Semantic queries must occur **outside active cognition loops**.

Timing is a form of power.
This policy removes that power.

---

## Allowed Query Windows

Semantic queries MAY occur only during:

1. **Pre-deliberation reflection**
   - Before any decision latch is armed
   - Before salience/value/urgency computation

2. **Post-episode analysis**
   - After an episode is closed
   - After control persistence is released

3. **Offline contexts**
   - Replay
   - Consolidation
   - Debugging
   - Analysis tools
   - Notebooks

These contexts are observational only.

---

## Forbidden Query Windows

Semantic queries MUST NOT occur during:

- `BrainRuntime.step`
- Decision latch evaluation
- Salience computation
- Value authorization
- Urgency integration
- Action selection
- Control persistence windows

If a semantic query can influence *when* a decision occurs,
this policy is violated.

---

## No Inline Queries Rule

Semantic queries MUST NOT be:

- Embedded in runtime loops
- Called conditionally on live state
- Used to gate execution paths

Semantic memory is **never consulted inline**.

---

## No Reactive Queries Rule

Semantic queries MUST NOT be triggered by:

- Near-threshold conditions
- Ambiguity detection
- Conflict detection
- Hesitation or uncertainty

Semantic memory must not become a fallback decision aid.

---

## Statelessness Requirement

Each semantic query MUST:

- Be stateless
- Produce no side effects
- Leave no residue in working memory
- Not alter subsequent cognition

Query results are ephemeral.

---

## Scheduling Enforcement

Any future semantic query adapter MUST:

- Require an explicit scheduling context
- Reject queries without declared timing
- Be auditable

Implicit or hidden queries are forbidden.

---

## Audit Invariant

Removing all semantic query calls MUST:

- Leave decision behavior unchanged
- Leave control flow unchanged
- Leave timing unchanged

If behavior changes, scheduling has been violated.

---

## Phase Boundary

Completion of Phase 7C authorizes:

- Design of guarded query schedulers
- Explicit query contexts (enums or tokens)
- Runtime *read-only* wiring

It does NOT authorize:

- Automatic semantic consultation
- Semantic-driven heuristics
- Decision shortcuts

---

End of policy.
