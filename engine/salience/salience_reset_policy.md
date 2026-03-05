# Salience Reset Policy — v0

Status: DESIGN-ONLY  
Phase: 6B (Reset Policy)  
Applies to: SalienceField  
Authority: NONE (authorization-only)

---

## Purpose

This policy defines constraints under which **salience state MAY be authorized
for attenuation across episode boundaries**.

Salience is the sole lawful source of dominance asymmetry.
Therefore, this policy is intentionally conservative.

This document does NOT implement behavior.
This document does NOT alter salience dynamics.
This document only defines future constraints.

---

## Definitions

- **Salience**: Transient gain applied to assemblies based on novelty, contrast, or surprise.
- **Episode Boundary**: A closed Episode recorded by episodic memory.
- **Reset**: Any attenuation, clearing, or decay acceleration of salience.
- **Authorization**: Permission only; never execution.

---

## Eligibility

Salience has been declared `ELIGIBLE` for episode-aware reset.

Eligibility does NOT imply default reset.

---

## Allowed Inputs (Read-Only)

A salience reset policy MAY observe:

- Episode.closed == True
- Episode.duration_steps
- Episode.has_decision()
- Episode.confidence (if present)
- Time since last episode boundary

A salience reset policy MUST NOT observe:

- Striatal dominance deltas
- CompetitionKernel internals
- GPi gate relief
- Decision latch counters
- Hypothesis routing
- Population activity directly

---

## Allowed Actions (Authorization Only)

If authorized, a salience reset MAY:

- Apply **uniform attenuation** across all salience entries
- Temporarily increase global salience decay rate
- Mark salience state as “expired” for downstream observers

A salience reset MUST NOT:

- Target specific channels or assemblies
- Introduce new salience
- Flip asymmetry direction
- Inject bias
- Influence routing or hypotheses
- Affect decision latch state

---

## Forbidden Actions (Hard Invariants)

A salience reset policy MUST NEVER:

- Clear salience immediately on episode close
- Perform a reset during active competition
- Operate during latch sustain window
- Operate post-commit while control is engaged
- Create or destroy dominance asymmetry
- Mask salience during ongoing deliberation

---

## Default Behavior (v0)

Under this version:

- Episode boundaries do NOT affect salience
- Authorization always returns FALSE
- Salience decays naturally as defined in Phase 3

---

## Rationale

Biological analogy:
Salience corresponds to sensory and associative novelty.
Novelty does not reset at task boundaries; it fades.

Aggressive salience resets risk:
- Artificial symmetry
- Suppressed learning signals
- Unstable deliberation dynamics

---

## Future Revisions

Possible future allowances:
- Soft attenuation after very long episodes
- Salience decay boost after low-confidence decisions
- Episodic tagging of salience peaks (no reset)

All future revisions require:
- New version
- Explicit tests
- Proof that dominance remains lawful

---
