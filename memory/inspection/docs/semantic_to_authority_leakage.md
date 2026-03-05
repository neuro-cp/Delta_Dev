# Failure Modes — Semantic → Authority Leakage

**Location:** `memory/inspection/docs/failure_modes/semantic_to_authority_leakage.md`

**Status:** Design-time guardrail (non-executable)

**Authority:** NONE

**Scope:** Defensive architecture for inspection-only semantic layers

---

## Purpose

This document enumerates *architectural failure modes* by which **semantic description** can quietly acquire **de facto authority** without any explicit execution or decision wiring.

It exists to prevent accidental violations of frozen invariants across:
- semantic activation
- semantic promotion eligibility
- inspection and diffing layers

This document introduces **no permissions**, **no behavior**, and **no code**.

---

## Invariant Being Defended

> Semantic artifacts may **exist**, **evolve**, and **be observed**, but must never:
>
> - influence execution
> - bias decisions or routing
> - justify action
> - harden into identity
> - acquire temporal or causal priority

Any mechanism that causes semantic signals to *feel* actionable—without explicit, checkpointed authority—is a violation.

---

## 1. Semantic Signal Gains De Facto Priority

### Violation

A descriptive semantic signal is implicitly treated as *more important*, *more urgent*, or *more correct* than other signals, despite having no authority.

This is not explicit execution.  
It is **priority by implication**.

---

### Mechanism (How This Sneaks In)

This failure mode typically enters through **apparently harmless descriptive fields**, such as:

- confidence-like scalar values
- stability labels that resemble readiness (e.g., “stable”, “converged”)
- normalized activation magnitudes that imply comparison
- aggregated inspection summaries that rank or order candidates

These are often justified as:

> “just metadata”

But metadata that implies *ordering* or *preference* is already halfway to authority.

---

### Where It Would Appear

This leakage can surface at any of the following boundaries:

- **Semantic Activation**
  - normalization or rescaling that implies cross-run comparability
  - windowed summaries that suggest importance rather than presence

- **PromotionCandidate Artifacts**
  - fields such as `confidence_estimate`, `stability_classification`, or tags that appear evaluative
  - schema additions that suggest readiness, likelihood, or merit

- **Inspection Reports**
  - summaries that sort, rank, or highlight candidates
  - language that implies recommendation rather than description

---

### Observable Symptom

One or more of the following becomes true:

- Reviewers begin asking:
  - “Why didn’t this get promoted?”
  - “This one looks stronger than the others.”

- Inspection output is read as *guidance* rather than *evidence*.

- Semantic artifacts are discussed as if they are **waiting for approval**, rather than **describing patterns**.

These are cultural symptoms of architectural leakage.

---

### Invariant Violated

This failure mode violates the core separation:

> **Description ≠ Authorization**

Once a semantic signal is perceived as having priority, it has functionally acquired authority—even if no code path exists.

---

### Required Audit Catch

This violation must be detectable via inspection-layer audits:

- Detection of scalar fields that imply ranking or confidence
- Detection of normalized values that enable comparison
- Inspection summaries that sort or prioritize candidates
- Language checks for prescriptive phrasing

Any such finding is an **architectural error**, not a tuning issue.

---

### Explicit Guardrail

The following must remain true at all times:

- Semantic activation values are **presence indicators**, not scores
- PromotionCandidate fields are **descriptive**, not predictive
- Inspection reports **describe** but never **recommend**

If a human can reasonably ask *“what should we do with this?”* after reading inspection output, the boundary has already been crossed.

---

## Non-Resolution Clause

This document does **not** propose fixes, thresholds, or mitigations.

Any attempt to “correct” this failure mode through execution, tuning, or policy is out of scope and requires a new checkpoint.

The only permitted response is **architectural refusal**.

---

_End of document._
