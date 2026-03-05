# Semantic Promotion Policy — v0

Status: ACTIVE (Policy Only)  
Phase: 10 — Gated Semantic Promotion  
Authority: NONE  
Scope: Semantic eligibility definition (no execution)

---

## Purpose

This policy defines the **conditions under which a semantic pattern
may become eligible** for long-term semantic memory.

This policy **does not perform promotion**.

It defines *what would qualify*, not *what will occur*.

---

## Core Principle

Semantic promotion is **earned through stability**, not salience.

A pattern must demonstrate:
- persistence across time
- recurrence across episodes
- independence from transient pressures

No single episode, insight, or reward may trigger promotion.

---

## Inputs (Allowed)

Promotion eligibility may consider:

- SemanticRecords
- DriftRecords (Phase 9B)
- Provenance metadata
- Episode indices (ordinal only)

Promotion eligibility MUST NOT consider:

- Runtime state
- Decision latch activity
- Value, urgency, or salience signals
- Control phase or execution context
- Human feedback or external labeling

---

## Eligibility Criteria (All Required)

A semantic pattern is *eligible* for promotion only if:

1. **Recurrence**
   - Appears in ≥ N distinct episodes  
   - Episodes are non-adjacent

2. **Persistence**
   - Observed across a minimum span of episodes  
   - DriftRecords indicate sustained presence

3. **Stability**
   - No significant volatility across windows  
   - Drift classification is stable or converging

4. **Independence**
   - Pattern occurrence does not correlate with:
     - urgency spikes
     - value modulation
     - forced decisions
   - Provenance shows neutral contexts

5. **Non-Dominance**
   - Pattern does not dominate semantic space  
   - Competing patterns coexist

*Thresholds are intentionally undefined in v0.*

---

## Explicit Disqualifiers

A semantic pattern MUST NOT be promoted if:

- It appears in only one episode
- It appears only during high urgency or value
- It is tied to a single decision outcome
- It decays immediately after first appearance
- It requires runtime context to interpret

---

## Temporal Separation

Promotion eligibility assessment is **offline only**.

It may run:
- after consolidation
- during replay
- during diagnostic analysis

It MUST NOT run:
- during runtime execution
- inside decision logic
- inside control or gating mechanisms

---

## Authority & Side Effects

This policy:
- grants NO authority
- creates NO memory
- triggers NO promotion
- mutates NO state

It defines **eligibility conditions only**.

---

## Versioning & Evolution

- Policy version increments on any rule change
- Schema changes require a new policy version
- Backward compatibility is NOT guaranteed
- Promotion logic (future) must reference a specific policy version

---

## Future Work (Non-Binding)

Possible future extensions:

- Promotion confidence estimation
- Multi-policy arbitration
- Domain-specific promotion rules

All extensions must preserve:
- offline execution
- non-authoritative behavior
- explicit versioning

---

End of policy.
