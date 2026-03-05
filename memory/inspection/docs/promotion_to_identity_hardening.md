# Failure Modes — Promotion → Identity Hardening

**Location:** `memory/inspection/docs/failure_modes/promotion_to_identity_hardening.md`

**Status:** Design-time guardrail (non-executable)  
**Authority:** NONE  
**Scope:** Defensive architecture for semantic promotion artifacts

---

## Purpose

This document enumerates architectural failure modes in which **PromotionCandidate artifacts**—intended to be advisory and discardable—quietly harden into **identity-bearing objects**.

This failure mode creates persistence *by narrative*, not by code.

---

## Invariant Being Defended

> Promotion artifacts describe **eligibility**, not **existence**.

A PromotionCandidate must never be treated as:
- an entity
- a memory
- a stable reference
- a thing that can be “carried forward”

---

## Violation

A PromotionCandidate is discussed, tracked, or referenced as if it *exists across time*, rather than being recomputed from evidence.

This is identity without authorization.

---

## Mechanisms

- Stable `semantic_id` reused conversationally across runs
- Candidates referenced without provenance context
- Reports comparing “the same candidate” across executions
- Human shorthand: “this semantic”, “that concept”, “it again”

---

## Observable Symptoms

- Questions like:
  - “Is this the same one as before?”
  - “Why hasn’t this been promoted yet?”
- Candidate counts treated as inventory
- Informal tracking outside inspection reports

---

## Invariant Violated

> **Eligibility ≠ Ontology**

Once a candidate is treated as a thing, identity has been smuggled in.

---

## Guardrail

- PromotionCandidates must be treated as **stateless renderings**
- No candidate may be referenced without full provenance
- Cross-run comparison must be structural, not referential

If a candidate can be named without recomputation, identity has already formed.

---

## Non-Resolution Clause

This document proposes no fixes or persistence mechanisms.

Any attempt to stabilize, store, or reference candidates requires a new checkpoint.

---

_End of document._
