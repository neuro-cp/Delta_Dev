# Semantic Ontology Policy — v0

Status: ACTIVE (Design Constraint)  
Authority: NONE  
Scope: Semantic Vocabulary Only  

---

## Purpose

This policy governs **how the semantic ontology may evolve**.

It exists to prevent ontology terms from becoming
implicit policy, preference, or control.

---

## Core Rule

Ontology defines **what may be said**,  
not **what may be done**.

---

## Permitted Changes

Ontology MAY evolve by:

- adding new descriptive terms
- refining definitions
- deprecating unused terms

ONLY if:
- changes are versioned
- changes are explicit
- no term implies action or value

---

## Forbidden Changes

Ontology MUST NOT:

- introduce ranking or ordering
- encode desirability or success
- define thresholds or criteria
- imply causality
- reference runtime signals
- influence promotion execution
- influence annotation visibility

Ontology MUST NOT act as soft policy.

---

## Enforcement Invariant

At all times:

- Removing ontology MUST NOT change behavior
- Ontology terms MUST NOT be executable
- Ontology MUST remain downstream of inspection

Violation is a hard architectural error.

---

## Versioning

- Any ontology change increments version
- No silent extensions
- No ad-hoc labels in code or schemas

---

## Lock Condition

This policy is binding until
semantic execution is explicitly authorized.

End of policy.
