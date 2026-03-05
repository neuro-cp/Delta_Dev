# Value Outcome Invariants

This document locks the invariants governing any future connection between episodic outcomes and Value.

Violating any invariant below requires an explicit phase reset.

---

## Core Invariants

1. **Proposal‑Only**

   * Outcomes may only emit `ValueProposal` objects.
   * No component may set Value directly.

2. **Offline Only**

   * Outcome interpretation must occur after replay/consolidation.
   * Runtime access is forbidden.

3. **Policy Sovereignty**

   * `ValuePolicy` is the sole authority on acceptance, magnitude, and timing.

4. **No Learning Semantics**

   * No reward
   * No optimization
   * No gradient
   * No persistence

5. **Bounded Influence**

   * All proposals are bounded by policy.
   * Value remains slow, tonic, and reversible.

6. **Inspection Mandatory**

   * Every proposal must be auditable post‑hoc.
   * Opaque heuristics are disallowed.

---

## Forbidden Patterns

* Direct decision → value writes
* Success/failure scalar rewards
* Long‑term accumulation of outcome scores
* Runtime coupling to latch or routing

---

## Removal Safety

Removing the entire outcome→value pathway must:

* Not change runtime behavior
* Not alter decisions
* Not alter memory

---

## Status

**LOCKED**
