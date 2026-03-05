# Semantic Annotation Schema — v0

Status: DRAFT  
Phase: 8A (Offline Semantic → Episodic Annotation)  
Authority: NONE  

Depends On:
- semantic_annotation_policy.md
- semantic_schema.md
- semantic_ontology.md
- episodic episode_structure

---

## Purpose

This schema defines the **structure of an annotation**
applied to a closed episode during offline replay.

Annotations are **descriptive metadata only**.
They do not alter episode structure, semantics, or behavior.

---

## Core Principle

Annotations describe **what an episode resembles**,  
using approved semantic ontology terms.

They do NOT:
- advise
- recommend
- evaluate
- influence action

Annotations are commentary, not instruction.

---

## Annotation Identity

Each annotation MUST have:

- `annotation_id`
  - Globally unique identifier
  - Stable across replays

- `episode_id`
  - Identifier of the annotated episode
  - An annotation belongs to exactly one episode

---

## Annotation Type

Each annotation MUST declare:

- `annotation_type`
  - Descriptive category string
  - MUST reference an allowed ontology kind
    (see `semantic_ontology.md`)

Examples:
- `"structural_frequency"`
- `"temporal_persistence"`
- `"decision_silence"`

Annotation types:
- are labels only
- carry no priority
- carry no authority

---

## Source Provenance

Annotations MUST record:

- `source_semantic_ids`
  - SemanticRecord identifiers referenced
  - Empty list permitted (rule-based annotations)

- `policy_version`
  - Annotation policy version

This ensures full auditability.

---

## Temporal Scope

Annotations MUST specify:

- `applied_during_replay`
  - Boolean (true for Phase 8A)

- `episode_closed`
  - Boolean confirming episode closure

Annotations MUST NOT apply to active episodes.

---

## Annotation Payload

### Descriptor (Required)

- Human-readable description
- MUST be explanatory only
- MUST NOT imply value or correctness

Examples:
- `"resembles structurally frequent single-decision episodes"`
- `"matches temporally persistent non-decisional pattern"`

---

### Metrics (Optional)

- Descriptive statistics only
- Examples:
  - counts
  - frequencies
  - spans
  - distances

Metrics MUST NOT include:
- scores
- utilities
- priorities
- thresholds

---

### Confidence (Optional)

- Float in `[0.0, 1.0]`
- Descriptive only
- MUST NOT be interpreted as belief or certainty
- MUST NOT gate behavior

---

## Ontology Constraint

Annotations:
- MAY reference ontology terms
- MUST NOT introduce new ontology terms
- MUST NOT reinterpret ontology semantics

Ontology governs vocabulary, not meaning strength.

---

## Mutability Rules

Annotations MUST be:

- Immutable once created
- Additive only
- Fully removable

Deleting all annotations MUST leave behavior unchanged.

---

## Explicit Prohibitions

Annotations MUST NEVER:

- modify episodes
- modify semantic records
- influence consolidation
- influence decisions
- persist executive state
- encode preferences
- act as triggers or conditions

Annotations are inert metadata.

---

## Storage Semantics

Annotations MAY be stored:

- adjacent to episodes
- in a separate annotation store
- in inspection-only tooling

Annotations MUST NOT be:

- read by runtime decision logic
- loaded into working memory
- cached across runs

---

## Versioning

Each annotation record MUST declare:

- `schema_version`
- `policy_version`

Breaking changes require:
- new schema version
- new tests
- explicit offline migration

---

## Phase Boundary

This schema authorizes:

- annotation record definitions
- offline annotation engines
- annotation inspection tooling

It does NOT authorize:

- learning
- runtime feedback
- semantic influence on action
- promotion execution

---

End of schema.
