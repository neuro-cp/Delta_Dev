# Influence Eligibility (Phase 16 — Design-Only)

This module defines **eligibility criteria**, not influence.

It answers:
> Under what conditions could a descriptive artifact
> be *considered* for proposing influence in a future phase?

It does NOT:
- apply influence
- compute gains
- bias routing
- affect runtime behavior
- trigger learning

Eligibility ≠ Authorization.

---

## Scope

Eligibility may reference:
- inspection reports
- diffs
- counts
- stability classifications

Eligibility may NOT reference:
- runtime state
- assemblies or populations
- salience, value, routing, or decision systems

---

## Removal Safety

Deleting this entire module must not change:
- runtime behavior
- learning behavior
- decision behavior

Only inspection output may differ.
