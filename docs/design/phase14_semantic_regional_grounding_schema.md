# Phase 14 — Semantic → Regional Grounding  
## Grounding Object Schema (Design-Only)

**Phase:** 14  
**Status:** Design-Only  
**Authority:** None  
**Execution:** Prohibited  
**Learning / Plasticity:** Prohibited  

---

## 1. Purpose

This document defines the **design-level schema** for semantic → regional grounding.

Grounding establishes a **descriptive association** between an existing,
promoted semantic entity and one or more neural regions.

Grounding does **not**:
- execute
- bias
- prioritize
- weight
- persist
- influence behavior

Grounding answers only:

> *Which regions is this semantic associated with?*

---

## 2. Grounding Object Definition (Conceptual)

A grounding object represents a **static association**.

### Conceptual Structure


---

## 3. Field Semantics

### semantic_id
- Must reference an existing `PromotedSemantic.semantic_id`
- Grounding must never create or promote semantics
- Invalid semantic IDs invalidate the grounding object

### grounded_regions
- A **set of region IDs**
- Region IDs must belong to the Phase-14 grounding scope
- Order is not meaningful
- Cardinality:
  - Zero regions is allowed
  - One or more regions is allowed

### notes
- Optional
- Human-readable explanation only
- Non-binding
- Never parsed, inferred, or interpreted

---

## 4. Explicit Prohibitions

A grounding object must **never** include:

- weights or strengths
- priorities or rankings
- timestamps
- decay rates
- provenance inference
- activation thresholds
- directionality
- population or assembly references
- subregional specificity
- any numeric fields

---

## 5. Authority Guarantees

Grounding objects:
- have no runtime surface
- have no replay surface
- have no learning surface
- have no inspection side effects

They may be:
- created
- inspected
- exported
- discarded

without changing system behavior.

---

## 6. Removal Safety

If all grounding objects are removed:
- runtime behavior must be identical
- replay behavior must be identical
- inspection output must differ only by absence of grounding sections

---

## 7. Final Assertion

Semantic grounding defines **where meaning could reside**  
without allowing meaning to **act**.
