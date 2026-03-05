# Runtime Annotation Visibility Policy — v0

Status: DRAFT  
Phase: 9A (Read-Only Annotation Visibility)  
Authority: NONE  
Depends On:
- semantic_annotation_policy.md
- annotation_schema.md
- semantic_query_policy.md
- semantic_query_scheduling_policy.md

---

## Purpose

This policy governs **if and when episodic annotations may be visible
to runtime cognition**.

Visibility does NOT imply influence.

Annotations may be *seen*,
but must never be *used to decide*.

---

## Core Principle

Annotations are **explanatory context**, not decision inputs.

They may explain *what just happened*,
but must not shape *what happens next*.

---

## Visibility Scope

Annotations MAY be visible only in the following contexts:

1. **Post-decision reflection**
   - After a decision has fully committed
   - After control persistence is engaged
   - After action selection is complete

2. **Pre-episode initialization**
   - Before any salience, value, or urgency is computed
   - Before decision latch arming
   - Before runtime step execution

Annotations MUST NOT be visible during:

- Decision evaluation
- Salience computation
- Value authorization
- Urgency integration
- Action selection
- Control arbitration

If annotation visibility overlaps with choice,
this policy is violated.

---

## Directionality


There is NO permitted path from annotations to:

- Salience
- Value
- Urgency
- Control gating
- Decision latch
- Motor output

Annotations are not signals.

---

## Visibility Constraints

Annotations MUST be:

- Read-only
- Non-persistent
- Non-cached
- Ephemeral

Annotations MUST NOT:

- Be copied into working memory
- Be transformed into features
- Be aggregated into scores
- Be ranked or filtered by “importance”

---

## Timing Guarantees

Annotation visibility MUST:

- Occur outside `BrainRuntime.step`
- Be explicitly scheduled
- Be auditable

Implicit or opportunistic access is forbidden.

---

## No Conditioning Rule

Annotations MUST NOT be used to:

- Bias attention
- Prime hypotheses
- Adjust thresholds
- Accelerate or delay decisions

Annotations may be *noticed*,
but never *acted upon*.

---

## Removal Invariant

Removing all annotation visibility MUST:

- Leave decision behavior unchanged
- Leave timing unchanged
- Leave outcome distributions unchanged

If not, visibility has become influence.

---

## Audit & Enforcement

Any runtime interface exposing annotations MUST:

- Declare visibility context
- Enforce read-only access
- Be testable for non-influence
- Be removable without side effects

---

## Phase Boundary

Completion of Phase 9A authorizes:

- Design of a visibility adapter
- Read-only annotation inspection hooks
- Post-decision explanation tooling

It does NOT authorize:

- Annotation-driven heuristics
- Runtime learning
- Preference shaping
- Policy updates

---

End of policy.
