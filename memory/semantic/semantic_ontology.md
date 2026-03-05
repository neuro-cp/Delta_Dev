# Semantic Ontology — v0

Status: DESIGN-ONLY  
Phase: 7 (Pre-Executable Semantics)  
Authority: NONE  

This document defines the **allowed vocabulary of meaning**
for the semantic layer.

The ontology constrains *what semantics may talk about*.
It does not define behavior, logic, or execution.

Removing this file MUST NOT change system behavior.

---

## Purpose

The semantic ontology exists to:

- prevent uncontrolled semantic sprawl
- standardize descriptive language across artifacts
- ensure semantics never acquire implicit authority
- separate *meaning labels* from *decision power*

This ontology is **descriptive only**.

---

## Core Principle

**Ontology defines language, not intent.**

Ontology terms:
- describe observed structure
- label recurring patterns
- provide shared reference for inspection

They MUST NOT:
- imply importance
- encode preference
- suggest action
- rank alternatives
- bias cognition or control

---

## Allowed Ontology Kinds

Only the following semantic kinds are permitted in v0.

### Structural
- `structural_frequency`
- `structural_density`
- `structural_co_occurrence`
- `structural_similarity`

### Temporal
- `temporal_persistence`
- `temporal_recurrence`
- `temporal_span`
- `temporal_transition`

### Decision-Related (Descriptive Only)
- `decision_presence`
- `decision_multiplicity`
- `decision_silence`

### Stability / Drift
- `stability_consistent`
- `stability_variable`
- `stability_novel`

No other ontology kinds are permitted without a versioned update.

---

## Allowed Axes of Description

Ontology terms may reference ONLY:

- time
- count
- frequency
- recurrence
- variance
- span
- density
- persistence

Ontology terms MUST NOT reference:

- utility
- value
- reward
- risk
- success
- correctness
- desirability
- confidence-in-action

---

## Mapping to Existing Artifacts (Non-Executable)

| Artifact | Field | Ontology Kind |
|--------|------|---------------|
| SemanticRecord | pattern_type = "frequency" | structural_frequency |
| DriftRecord | is_persistent = True | temporal_persistence |
| DriftRecord | density | structural_density |
| PromotionCandidate | stability_classification | stability_consistent / stability_variable |
| Annotation | descriptor | (references ontology only) |

Mappings are **labels only**.
They do not imply transformation or logic.

---

## Negative Space (Hard Prohibitions)

Ontology MUST NEVER:

- influence runtime execution
- influence salience, value, urgency, or routing
- appear inside `BrainRuntime.step`
- be consulted during decision evaluation
- be converted into scores or priorities
- be used to justify promotion or suppression

If removing ontology changes behavior, the system is invalid.

---

## Versioning Rules

- Ontology changes require a new version
- New terms MUST be explicitly enumerated
- Backward compatibility is preferred but not required
- No silent extension is permitted

---

## Lock Condition

This ontology is binding until:

- semantic execution is explicitly authorized
- promotion execution is defined
- regression guards exist

Until then:

**Ontology is language only.**

End of ontology.
