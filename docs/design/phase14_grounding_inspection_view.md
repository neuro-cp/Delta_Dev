# Phase 14 — Semantic → Regional Grounding  
## Inspection View Contract

**Phase:** 14  
**Scope:** Inspection-Only  
**Authority:** None  

---

## 1. Purpose

This document defines how semantic → regional grounding appears in
**inspection output only**.

The inspection view:
- is human-facing
- is descriptive
- is immutable
- carries zero authority

---

## 2. Placement in Inspection Report

Grounding appears as an **optional section** within the inspection report.

It must:
- never replace existing sections
- never modify counts or summaries
- never affect audits

Grounding visibility is **additive only**.

---

## 3. Conceptual View Structure

SemanticRegionalGroundingView
├── semantic_id: str
├── grounded_regions: List[str]
└── notes: Optional[str]


---

## 4. Construction Rules

The inspection view:
- reads grounding objects only
- performs no inference
- performs no aggregation
- performs no validation beyond existence

Grounding views:
- must not depend on runtime state
- must not depend on replay state
- must not depend on activation or learning artifacts

---

## 5. Immutability Guarantees

Inspection grounding views must be:
- frozen / immutable
- deterministic
- reproducible
- safe to discard and rebuild

---

## 6. Explicit Prohibitions

Inspection grounding must never:
- compute importance
- rank semantics
- compare regions
- imply causality
- imply directionality
- introduce numeric interpretation

---

## 7. Audit Compatibility

Grounding views:
- are excluded from authority audits
- are excluded from influence audits
- are excluded from saturation audits

They are **explanatory only**.

---

## 8. Final Assertion

Inspection shows **what exists**, not **what acts**.

Grounding visibility must never be mistaken for influence.
