# Semantic Grounding (Phase 14)

This folder implements **Phase 14: Semantic → Regional Grounding**.

Grounding is **descriptive anatomy**, not cognition.

It answers:
> Where could this semantic concept plausibly reside?

It does NOT answer:
- how strongly
- how often
- when
- why
- with what effect

---

## Design Principles

- Zero authority
- Zero execution
- Zero learning
- Zero inference

---

## Folder Contents

- `grounding_scope.py`  
  Defines the allowed region set.

- `grounding_record.py`  
  Immutable grounding data object.

- `grounding_registry.py`  
  Read-only storage.

- `inspection_adapter.py`  
  Inspection-only visibility.

- `grounding_policy.md`  
  Binding human-readable rules.

---

## Relationship to Other Systems

- Depends on: semantic promotion (existence)
- Visible via: inspection only
- Independent of: runtime, cognition, learning

---

## Status

Phase 14 is **design-only**.

No file in this folder may introduce authority without
explicit phase reopening.
