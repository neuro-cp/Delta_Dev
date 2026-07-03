# Runtime V1.4C Architecture Decision Lock + Output Trace Design

Generated: `2026-07-02`

Final recommendation: `PROCEED_FEEDBACK_CAPTURE_SCAFFOLD`

## 1. Summary

Runtime V1.4C locks the immediate DELTA trajectory and adds an inert output
trace design. It does not train, prune, mutate canonical storage, route live
specialists, call providers, or change Model B/HYB1 defaults.

V1.4C exists to protect DELTA's core philosophy:

- cognition before action
- evidence before confidence
- reversible correction before permanent mutation
- lane-specific use before global concept judgment
- uncertainty before hallucinated output
- replay/consolidation before canonical learning
- specialist routing as evidence acquisition, not authority transfer

## 2. Current V1.3/V1.4A/V1.4B State

Runtime V1.3:

- Model B remains default.
- HYB1 is dormant/env-gated only.
- HYB1 flag: `DELTA_RUNTIME_V13_HYB1_ENABLED=true`.
- V1.3 variant work is stopped.

Runtime V1.4A:

- evidence role metadata scaffold completed
- lane-specific permission scaffold completed
- pruning / negative feedback record schema scaffold completed
- CandidateEnvelope lifecycle scaffold completed
- original DELTA gap map completed

Runtime V1.4B:

- output discipline scaffold completed
- unknown-answer port scaffold completed
- dormant specialist router scaffold completed
- no provider calls
- no live routing
- no default behavior changed

## 3. Why V1.4C Exists

Future learning, pruning, replay, and canonical memory all need a clean record
of what happened during an answer. Without that trace, DELTA would have to learn
from messy logs or implicit runtime side effects.

V1.4C creates the bridge from:

`DELTA can answer safely`

to:

`DELTA can later learn from answers safely`

## 4. Architecture Decision Table

| Concept | Status | Decision | Activation Dependencies |
| --- | --- | --- | --- |
| sleep replay consolidation | accepted | scheduled/batch replay-consolidation, not literal sleep | output traces; feedback records; replay validator |
| live pruning projection | accepted | temporary runtime/session projection only | answer traces; feedback events; replay validator; lane permissions |
| canonical pruning | deferred | wait for repeated evidence, provenance, rollback, or human approval | live canonical store; provenance ledger; rollback; human review |
| negative feedback memory | accepted | append-only feedback and pruning-review records | answer traces; failure taxonomy |
| episodic capture | deferred | explicit and auditable capture after trace policy | output trace design; feedback capture; privacy/scope policy |
| episodic-to-semantic consolidation | deferred | trace-backed candidate envelopes, no direct canonical writes | CandidateEnvelope; feedback records; replay queue; canonical store design |
| live canonical store | deferred | schema shaped by output traces first | trace usage requirements; provenance; rollback; promotion ledger |
| candidate envelope | accepted | scaffolded lifecycle carrier for future controlled learning | feedback records; replay design |
| structural semantic adapter | accepted | schema-first signal tagging, no active routing yet | signal precision audit; role assignment validation |
| evidence role metadata | accepted | scaffolded inert metadata | role validation |
| lane permissions | accepted | scaffolded; active enforcement waits | policy provenance; runtime integration tests |
| hypothesis arbitration | deferred | wait for evidence roles and contradiction direction | evidence roles; confidence trajectory; contradiction direction |
| confidence inertia | deferred | reporting first, no active smoothing | trace history; feedback history |
| DMSA/multi-stream assessment | accepted | report-only multi-check validators, not executor | stable evaluator roles; veto rules |
| execution authorization | deferred | no action runtime until authorization packet exists | action taxonomy; authorization ledger; output discipline integration |
| unknown answer port | accepted | scaffolded output discipline | response integration tests |
| specialist routing | deferred | dormant route objects only; no provider calls | output discipline; feedback capture; provider authorization; merge rules |
| controlled training | deferred | waits for traces, feedback, replay, canonical store | output traces; feedback capture; replay; live canonical store; rollback |
| autonomous knowledge acquisition | deferred | wait for pruning/source/replay/canonical controls | source credibility; authorization; canonical store; replay; pruning controls |

## 5. Sleep/Replay Consolidation Decision

Sleep stays as a DELTA concept, but implementation should be scheduled/batch
replay-consolidation. It should not become a mystical or free-running mode.

Activation waits for:

- output traces
- feedback records
- replay validator

## 6. Live Pruning vs Canonical Pruning Decision

Live pruning is accepted only as temporary runtime/session projection. Early
pruning must be reversible and lane-specific.

Canonical pruning is deferred until DELTA has:

- replay/consolidation
- repeated evidence
- provenance
- rollback
- or human approval

## 7. Canonical Memory Timing Decision

Canonical memory does not come next. Output traces should shape the canonical
schema first. This avoids freezing a permanent store before DELTA knows what
runtime evidence, uncertainty, routing, and feedback metadata it actually needs.

## 8. Specialist Routing Decision

Specialist routing remains dormant. The current router can draft route objects,
but no provider calls are allowed. Specialist routing is evidence acquisition,
not authority transfer.

## 9. Training Decision

Training remains disabled. Controlled learning waits for:

- output traces
- feedback capture
- replay/consolidation
- live canonical store design
- rollback

## 10. Output Trace Design

V1.4C adds:

- `AnswerTrace`
- `EvidenceUseTrace`
- `FeedbackEventDraft`
- `ReplayCandidateMarker`

Trace records capture:

- the question
- answer mode
- evidence use by lane
- risk flags
- confidence
- uncertainty reason
- specialist route domain
- whether a specialist was called
- final answer summary

## 11. How Output Traces Prepare Feedback/Replay/Pruning/Learning

Output traces provide the future input for:

- feedback capture: what did the user confirm, correct, or reject?
- replay: which trace deserves review or replay?
- pruning: which lane/context caused drift?
- controlled learning: which candidate should be consolidated?

They remain non-mutating records. They do not train, prune, promote, route, or
call providers.

## 12. User Decision Points

- Should episodic capture store every answer trace or only flagged traces?
- Should sleep/replay run on a schedule, explicit command, or both?
- Should pruning projections ever persist across sessions before canonical v1?
- Should specialist calls require explicit user approval every time?
- Should DMSA stay a report-only scorecard through V1.4?
- What exact authorization packet is required before DELTA can execute actions?

## 13. Safety Boundaries Preserved

- training: `False`
- live pruning: `False`
- canonical mutation: `False`
- Model B default changed: `False`
- HYB1 default enabled: `False`
- specialist provider calls: `False`
- benchmark fixtures changed: `False`
- provider prompts changed: `False`
- live routing: `False`
- action execution: `False`

## 14. Recommended Next Phase

Proceed to `Runtime V1.4D - Feedback Capture Scaffold`.

The next phase should turn output traces into structured feedback drafts without
learning from them yet.

## 15. Continuation Checkpoint

- `runtime_v13_complete`: `True`
- `model_b_default_remains_active`: `True`
- `hyb1_dormant_only`: `True`
- `v14a_safe_scaffold_complete`: `True`
- `v14b_output_discipline_scaffold_complete`: `True`
- `v14c_architecture_decision_lock_complete`: `True`
- `v14c_output_trace_design_complete`: `True`
- `training_enabled`: `False`
- `live_pruning_enabled`: `False`
- `canonical_writes_enabled`: `False`
- `specialist_provider_calls_enabled`: `False`
- `next_step`: `PROCEED_FEEDBACK_CAPTURE_SCAFFOLD`

PROCEED_FEEDBACK_CAPTURE_SCAFFOLD
