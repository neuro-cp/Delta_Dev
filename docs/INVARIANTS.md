# DELTA Invariants

This document defines rules future Delta work must preserve. These are not
roadmap items or feature goals; they are substrate invariants.

## Authority

- Experience memory is append-only.
- Knowledge is derived, never silently rewritten.
- Provenance is never lost.
- Contradictions are linked, not erased.
- Reasoning providers propose; Delta governs.
- Agency proposes; execution remains bounded and explicit.
- No subsystem receives hidden execution authority.

## Reasoning Providers

- Reasoning providers are interchangeable cognitive components.
- Delta's objective is capability integration, not provider competition.
- Provider identity is an implementation detail, not a user-facing cognitive
  identity.
- Persistent memory, knowledge, evidence, governance, goals, and self-model
  state belong exclusively to Delta.
- Providers may contribute reasoning, planning, retrieval, translation,
  mathematics, coding, vision, speech, search, or external tool capability, but
  none of those providers owns Delta's cognition.
- Capability selection should decide what kind of cognition is needed before
  selecting a provider that can contribute it.
- Provider comparison is a diagnostic instrument. It must not turn Delta into a
  leaderboard, benchmark suite, or model-facing product.
- Codex is Delta's engineering mentor, not the author of Delta's cognition.
  Codex may inspect reports and propose system improvements, but it must not
  directly edit Delta's memories, beliefs, goals, or self-model as cognition.

## Evidence And Justification

- Evidence is the canonical justification for knowledge promotion, prediction
  validation, contradiction resolution, self-model assessment, and confidence
  revision.
- Experiences are not knowledge.
- Generated provider experiences must enter governance before they can support
  persistent knowledge.
- No persistent knowledge may change without evidence.
- Confidence is derived from justification; it must not become an unexplained
  mutable state variable.
- Every confidence change must be explainable through supporting evidence,
  counter-evidence, validation history, contradiction pressure, and provenance.
- Every knowledge revision must preserve what evidence caused the belief to
  change.
- Delta should always be able to answer: what evidence changed this belief?

## State

- Append-only history must not be mistaken for current truth.
- Current-state metrics must resolve latest valid revisions.
- Every persistent record should remain traceable to its origin.
- Every promoted knowledge record must preserve source evidence.
- Every prediction should remain traceable through its lifecycle.
- Duplicate suppression must prevent repeated cycles from creating duplicate
  knowledge without new evidence.

## Cognition

- Every cognitive cycle should be observable.
- Every important decision should be explainable.
- Every region should have a single responsibility.
- Every subsystem should participate in the canonical cognitive cycle or remain
  clearly outside it as a tool/client.
- Interfaces such as chat, coding, automation, robotics, dashboards, and APIs
  are clients of the substrate, not the substrate itself.
- Do not optimize Delta around a single interface.

## Development

- Prefer governance, observability, reproducibility, and metric accuracy over
  adding new top-level regions.
- Treat runtime experiments as evidence.
- Reports must distinguish observed behavior from aspiration.
- Documentation must be sufficient for a cold Codex session to resume without
  rediscovering context.

## Runtime V1.3 Defaults

- Runtime V1.3's accepted no-env default is Model B contextualized corpus
  support plus the `citation_context` reasoning usage gate.
- Experimental variants must remain dormant unless an explicit environment flag
  enables them.
- `DELTA_RUNTIME_V13_HYB1_ENABLED=true` enables only the HYB1 dormant prototype.
  HYB1 must not become the default without a separate validation pass.
- Dormant runtime variants must preserve read-only behavior and must not modify
  learning, governance, storage, provider prompts, candidate stores, canonical
  storage, or benchmark fixtures.
