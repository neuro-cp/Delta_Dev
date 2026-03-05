# Semantic → Assembly Hypotheses (Phase 15)

This module provides **descriptive hypotheses** linking
*promoted semantics* to **assemblies within regions**.

It exists to improve interpretability and future auditability,
not to drive behavior.

## What this is
- Offline
- Immutable
- Inspection-only
- Symbolic (assemblies are opaque identifiers)

## What this is not
- Not routing
- Not salience
- Not value
- Not learning
- Not execution
- Not authority

Assemblies do not know this exists.
Runtime cannot import this module.

## Relationship to other layers
- Depends on: promoted semantics (existence)
- Constrained by: Phase-14 semantic grounding scope
- Visible via: inspection only
- Independent of: cognition dynamics, replay, learning

Removal safety: deleting this entire folder must not change
any system behavior or learning outcomes.
