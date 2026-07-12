# LUNA-Style Structural Exploration

## What DELTA Currently Is

DELTA is a governed local cognitive desktop application with a broad historical substrate and a smaller live operational spine. The active spine accepts operator turns, handles local knowledge and text-only Wikipedia evidence, compares evidence to local concepts, creates reviewable developmental observations, maintains a bounded operational self-model, and asks for approval before consequential actions.

It is not an unconstrained agent and should not be described as one. It has no provider authority, no automatic persistent learning, no runtime repository authority, and no independent background model-call policy.

## Structural Assessment

The best design move in the repair was not to make the controller infer autonomously. Instead, the operator-approved local-model request became an explicit event crossing a controlled boundary. That keeps the human-visible conversational flow, model resource lifecycle, and controller journal mutually legible.

The least elegant part is concentration of responsibility. `DELTA.py` is a large desktop surface with legacy compatibility and new worker logic. The live bridge is similarly overloaded. The router contains many direct phrase patterns that were useful in fast milestone development but obscure a smaller production spine.

## Developmental Potential

The system has the pieces needed for a useful development loop:

- evidence can create an observation;
- an observation can form a bounded initiative;
- the controller can represent an objective and an operator inquiry;
- an approved model turn can assist explanation or planning;
- promotion remains reviewable.

The next developmental step should be quality and continuity, not more permissions. It should measure whether initiatives are valuable, nonduplicative, and quiet enough over a real operator session.

## Identity and Continuity

Identity should stay separate from purpose, permissions, and canonical memory. The existing `UNDEFINED` identity state and reversible review proposal are healthy. A future identity proposal should be backed by observed interaction traits, a session-stability period, an operator-readable diff, and an explicit rollback. It should never be inferred from a single model output or used to authorize behavior.

## Local Models

The observed division of labor is credible:

- Llama: conversation and reasoning-analysis turns.
- Mistral: planning turns.
- Deterministic controller and self-model: lifecycle, authority, status, budgets, and correlation.

The next gain is not adding a third model. It is making model outcome quality observable: concise user rating, completion quality, failure reason, latency, residency, and whether the deterministic layer had to override a model suggestion.

## Operator Experience

The worker queue makes the system feel more continuous because it responds to controls while work is active. The next UX work should make state transitions calmer: one consent question, visible current action, a quiet digest for nonurgent initiatives, and a compact history of why something was surfaced. The UI should remain a trust surface, not a stream of internal machinery.

## Ranked Roadmap

1. Run a real-model multi-hour operator pilot with external metrics and a limited notification policy.
2. Extract the live-turn coordinator and pending-action envelope from UI/bridge code.
3. Add fake-manager model scenarios to the behavioral campaign and record model-specific invariants.
4. Clarify model registry counts and status semantics.
5. Add controlled initiative quality evaluation and digest behavior.
6. Design session continuity/restart reconciliation for explicitly pending actions without hidden persistence.
7. Explore identity evidence and rollback only after the first two operational pilots.
