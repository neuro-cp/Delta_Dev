# Post‑Decision Outcome → Value (Design‑Only)

## Purpose

Define a lawful, auditable path by which **post‑decision episodic outcomes** may *propose* changes to the **Value** system **offline**, without introducing learning, authority, or runtime feedback.

This document is **design‑only**. No runtime wiring, no mutation, no policy changes.

---

## Definitions

**Outcome**
A descriptive summary derived from a **closed episode** after replay/consolidation. Outcomes are *observations*, not judgments.

**Value Proposal**
A `ValueProposal(delta, source, note)` emitted by an offline process. Proposals are advisory and may be rejected by policy.

---

## Authoritative Boundaries

* Episodes are owned by `EpisodeTracker` (state‑only).
* Events are logged in `EpisodeTrace` (forensic, append‑only).
* Alignment happens via `EpisodeReplay` (read‑only, offline).
* Structure is summarized by `EpisodeConsolidator` (immutable records).
* Value changes are gated exclusively by `ValuePolicy`.

No component in this chain may mutate runtime state.

---

## Lawful Flow (Offline)

1. **Decision occurs** → episode eventually closes.
2. **EpisodeReplay** aligns closed episodes with trace/salience (read‑only).
3. **EpisodeConsolidator** produces immutable consolidation records.
4. **Outcome Interpreter (offline)** inspects consolidation records and *suggests* ValueProposals.
5. **ValuePolicy** later decides acceptance when/if proposals are applied.

At no point does an outcome directly modify Value.

---

## What Outcomes May Inspect

* Episode duration (steps/time)
* Decision count
* Inter‑decision intervals
* Whether episode ended by decision or timeout
* Tags (if present)

What outcomes **must not** inspect:

* Internal neuron activity
* Policy thresholds
* Bias registry contents
* Future episodes

---

## Why This Is Not Learning

* No gradient
* No credit assignment
* No reward maximization
* No persistence beyond proposal emission
* No parameter updates

Value drifts **tonically**, not optimally.

---

## Audit & Inspection

Any outcome‑derived ValueProposal **must** be representable in Inspection reports:

* source
* delta
* rationale (note)
* episode_id reference

If it cannot be inspected, it does not exist.

---

## Non‑Goals

* Reinforcement learning
* Q‑values
* Temporal difference updates
* Runtime feedback
* Autonomous value escalation

---

## Status

**DESIGN‑ONLY · LOCKED UNTIL FUTURE PHASE**
