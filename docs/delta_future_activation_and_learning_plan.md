# DELTA Future Activation And Learning Plan

This is a planning artifact only. It does not change runtime behavior, activate
memory, enable recall, promote HYB1, call providers, execute actions, or train
model weights.

## 1. Current State

Latest verified phase: Runtime V1.5E local knowledge inventory answer router.

Active capabilities:

- manual local console questions through `scripts/ask_delta.py`
- deterministic local self-knowledge routing
- raw/semantic preview trace generation
- safety status output
- repo-local report/test self-inspection

Disabled capabilities:

- provider calls
- tool calls
- action execution
- memory writes
- canonical writes
- runtime recall mutation
- active recall bridge
- specialist routing
- HYB1 default activation
- training, fine-tuning, and model weight updates
- dataset export
- background schedulers, listeners, workers, timers, and queues

Model B status: Model B remains the default runtime baseline.

HYB1 status: HYB1 remains dormant and environment-gated. It is not promoted and
is not enabled by default.

Current `ask_delta.py` behavior: the console can answer known repo-local DELTA
self-knowledge questions deterministically and returns trace/safety output. It
does not persist memory or call providers.

Current limitation: DELTA can answer local scaffold/status questions through
the V1.5E router, but it still cannot answer arbitrary world questions without
future provider/model integration or activated governed recall.

## 2. Near-Term V1.5 Sequence

Recommended order:

1. V1.5E Local Knowledge Inventory Answer Router
2. V1.5F Self-Question Test Pack
3. V1.5G Feedback -> Memory Candidate Proposal
4. V1.5H Human-Approved Canonical Memory Write Trial
5. V1.5I Recall Bridge Limited Trial
6. V1.5J Demo Script / Showcase Report

## 3. First Demonstrable Loop

Target demo:

```text
User asks DELTA about itself
  -> DELTA answers from local repo knowledge
  -> user corrects DELTA
  -> DELTA captures correction as feedback
  -> DELTA proposes memory candidate
  -> user approves
  -> DELTA writes canonical memory with audit trace
  -> later recall surfaces approved memory as candidate context
```

The first implementation must keep proposal separate from mutation. A feedback
record is not a memory write, and a memory candidate is not canonical memory.

## 4. Validated Experience Learning Loop

Future V1.6A should design:

- unknown detection
- evidence acquisition path
- candidate answer
- user validation/correction
- beneficial experience score
- replay candidate
- selectivity adjustment candidate
- consolidation candidate
- human review gate

Core invariants:

- validation signal != truth
- correction signal != canonical memory
- beneficial experience != automatic promotion
- selectivity tuning proposal != live tuning

## 5. Daily External Consolidation Evaluator

Future V1.6B/V1.6C may package relevant stores and candidates once per day for
external evaluator review:

- user confirmations
- corrections
- unresolved unknowns
- replay candidates
- consolidation candidates
- selectivity adjustment candidates
- specialist/SLM answers
- action-intent events
- contradictions
- high-impact preferences

Evaluator checks:

- evidence quality
- sarcasm
- ambiguity
- misuse
- malicious intent
- bad confirmations
- contradictions
- overfitting risk
- unsafe memory proposals

Evaluator may recommend:

- promote
- defer
- reject
- needs human review
- contradiction detected
- sarcasm/ambiguity likely
- malicious/manipulative signal likely
- insufficient evidence
- selectivity adjustment should narrow route
- selectivity adjustment should be rejected

Evaluator must not:

- write memory
- change routing weights
- delete records
- activate tools
- train model
- change persona
- promote HYB1
- mutate canonical memory
- mutate runtime recall

Core invariants:

- external evaluator != authority
- daily review != automatic promotion
- sarcasm detection != certainty
- misuse flag != deletion
- correction proposal != applied correction
- selectivity review != live tuning
- API result != canonical memory

## 6. Persona / Identity Development

Future identity work should wait until the memory/recall loop is governed.

- user chooses starting assistant name/persona
- DELTA may later propose identity updates based on approved interaction history
- user must approve identity changes
- identity changes are memory-gated and auditable

Core invariant: identity can emerge from interaction, but identity changes
require consent.

## 7. Risk Register

- overfitting to one user
- sarcasm mistaken as confirmation
- malicious confirmations
- premature memory writes
- HYB1 accidental promotion
- provider/evaluator treated as authority
- action execution before ledger/approval
- background scheduler introduced too early
- generic agent drift

## 8. Recommended Next Marathon

Recommended safe implementation marathon:

1. V1.5E Local Knowledge Inventory Answer Router
2. V1.5F Self-Question Test Pack
3. V1.5G Feedback -> Memory Candidate Proposal
4. V1.5H Human-Approved Canonical Memory Write Trial Design only, unless the
   user explicitly authorizes an actual local write trial later.

Safety boundary: do not implement live training, live pruning, canonical writes,
provider calls, active recall, active specialist routing, or action execution as
part of this marathon.
