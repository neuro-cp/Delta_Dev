# Semantic Memory Schema — v0

Status: DRAFT  
Phase: 6 (Semantic Memory)  
Authority: NONE  
Derived From: Episodic Consolidation (Phase 5B)

---

## Purpose

This document defines the **canonical schema** for semantic memory records.

A semantic record is a **lossy, low-entropy abstraction**
derived from many episodic observations.

Semantic records describe **regularities**, not events.
They do not decide, act, bias, or evaluate.

This schema defines *shape only*.
It does not imply implementation.

---

## Core Definition

A **SemanticRecord** represents a statistically stable pattern
observed across multiple episodes.

It answers:

- “What tends to occur?”
- “How often does this structure appear?”
- “What relationships recur?”

It does NOT answer:

- “What should be done?”
- “What matters most?”
- “What is good or bad?”

---

## SemanticRecord (Conceptual Structure)

SemanticRecord
├─ semantic_id
├─ policy_version
├─ schema_version
│
├─ provenance
│ ├─ episode_ids
│ ├─ consolidation_ids
│ ├─ sample_size
│
├─ temporal_scope
│ ├─ first_observed_step
│ ├─ last_observed_step
│ ├─ observation_window
│
├─ pattern
│ ├─ pattern_type
│ ├─ pattern_descriptor
│
├─ statistics
│ ├─ count
│ ├─ frequency
│ ├─ distributions
│ ├─ confidence_intervals
│
├─ stability
│ ├─ support
│ ├─ variance
│ ├─ decay_rate
│
├─ tags
│
└─ notes


---

## Field Semantics

### semantic_id
- Stable identifier for this semantic abstraction
- Deterministically derived
- Never reused for different semantics

---

### policy_version
- Semantic policy version under which this record was produced
- Used to enforce compatibility

---

### schema_version
- Semantic schema version
- Required for migration and replay

---

## Provenance

Semantic memory MUST retain traceability.

### episode_ids
- List of contributing episode identifiers
- May be truncated or hashed for storage

### consolidation_ids
- References to Phase 5B consolidation records
- Ensures semantic memory never bypasses episodic structure

### sample_size
- Number of episodes contributing evidence
- Single-episode semantics are forbidden

---

## Temporal Scope

### first_observed_step
- Earliest step where this pattern was observed

### last_observed_step
- Most recent step contributing evidence

### observation_window
- Span across which the pattern has been observed

---

## Pattern Description

### pattern_type
Allowed values include (non-exhaustive):

- frequency
- sequence
- co_occurrence
- duration
- transition

Pattern types are **descriptive only**.

### pattern_descriptor
- Minimal description of the observed structure
- May include symbolic or categorical representation
- MUST NOT encode goals, values, or preferences

---

## Statistics

### count
- Total number of observations

### frequency
- Normalized occurrence rate

### distributions
- Optional statistical distributions
- Mean, median, variance, histograms, etc.

### confidence_intervals
- Statistical confidence only
- Not belief confidence or correctness

---

## Stability

Semantic memory favors persistence.

### support
- Strength of evidence (e.g., observations per window)

### variance
- Stability of the pattern over time

### decay_rate
- Rate at which unused semantics weaken
- Decay MUST be slow and conservative

---

## Tags

- Descriptive labels only
- No evaluative language
- No operational meaning

Examples:
- `"recurrent"`
- `"long_duration"`
- `"rare_sequence"`

---

## Notes

Optional human-readable annotations.

Notes:
- Have no machine authority
- Must not be parsed by runtime
- Are not required for correctness

---

## Explicit Prohibitions

SemanticRecord MUST NOT contain:

- Value or reward signals
- Salience or priority
- Action recommendations
- Preferences or goals
- Decision thresholds
- Runtime hooks or references

If a field can influence behavior directly,
it does not belong in this schema.

---

## Invariants

The following invariants MUST always hold:

- Semantic records are offline-generated
- Semantic records are immutable once written
- Semantic records are discardable and recomputable
- Semantic records do not influence runtime execution

Violation of these invariants is a hard architectural error.

---

## Future Evolution

Changes to this schema require:

- New schema version
- Updated semantic policy
- Offline migration logic
- Dedicated tests

Backward compatibility is preferred but not required.

---
----
update

Ontology Alignment

pattern_type MUST reference a term defined in semantic_ontology.md

Ontology terms are descriptive only

Ontology alignment

End of schema.


