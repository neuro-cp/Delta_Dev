# Runtime V1.4 Architecture Reconciliation Checkpoint

Generated: `2026-07-02`

Final recommendation: `REQUEST_USER_ARCHITECTURE_DECISIONS`

## 1. Summary

Runtime V1.3 is complete and Runtime V1.4A/B safe scaffolds now exist. The
repo has enough structure to represent evidence roles, lane permissions,
candidate envelopes, reversible pruning proposals, calibrated output states, and
dormant specialist routes.

This checkpoint pauses before sleep/replay, live pruning, live canonical memory,
specialist routing, or controlled training. The main risk is not missing code.
The main risk is letting implementation drift away from the original DELTA
vision by turning metaphors like sleep, pruning, routing, and training into
generic subsystems without preserving their intended cognitive role.

## 2. Why Reconciliation Is Needed

The recent implementation has been intentionally conservative:

- no training
- no live pruning
- no canonical writes
- no provider calls
- no provider prompt changes
- no runtime default changes

That safety is useful, but the original DELTA vision includes larger concepts
that are not simply "more runtime code." They need explicit translation into
repo-native mechanisms before they are implemented. This report maps each
original concept to the current repo state and marks where user decisions are
needed.

## 3. Current V1.3 Final State

- Model B remains the default runtime.
- HYB1 remains dormant and env-gated only with
  `DELTA_RUNTIME_V13_HYB1_ENABLED=true`.
- No V1.3 variants should be run unless explicitly requested.
- Model B is the stable safety baseline.
- HYB1 is a dormant improvement candidate, not a default behavior.

## 4. Current V1.4 Corpus Sufficiency Result

The V1.4 corpus sufficiency audit concluded that more training is not currently
the right answer:

- final recommendation: `CHECKPOINT_NO_TRAINING_NEEDED`
- permanent training justified now: `False`
- no remaining miss was classified as concept absent
- most misses were redundant, buried, benchmark/live-window limited, or required
  a new live-safe signal

This supports the current direction: build safe scaffolding and reconcile the
architecture before enabling training or canonical memory mutation.

## 5. Original DELTA Concept Reconciliation Table

| Concept | Original intended function | Current repo equivalent | Status | Risk if implemented now | Dependencies | Recommended implementation form | Roadmap? | User decision required? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sleep cycle / replay consolidation | Offline review of experiences, failures, and candidate memories to strengthen or weaken knowledge without live pressure. | Report-only replay, validation reports, V1.4 CandidateEnvelope schema. | `absent` | Could mutate memory before rollback/provenance exists. | live store design, CandidateEnvelope integration, negative feedback records. | scheduled batch replay over envelopes, no provider calls initially, report-only first. | yes | yes |
| live pruning | Reduce harmful concept pathways during use. | V1.4 pruning projections and lane dampening records. | `scaffold only` | Deleting or suppressing useful knowledge from one bad case. | lane permissions, feedback records, reversibility policy. | reversible dampening projection only; no deletion. | yes | yes |
| selective pruning / corrective dampening | Weaken concepts only in the lane/context where they caused failure. | `PruningRecord`, `CorrectiveAction`, lane policies. | `scaffold only` | Overgeneralized dampening could damage recall. | failure context hash, affected lane, recovery criteria. | append-only negative feedback plus lane-scoped dampening simulation. | yes | no |
| canonical pruning | Remove or demote canonical knowledge that is proven corrupt or harmful. | none; only candidate-store governance exists. | `absent` | High risk without canonical rollback. | canonical v1, provenance ledger, promotion/demotion ledger. | governed demotion ledger after live canonical store exists. | yes | yes |
| negative feedback memory | Remember when a concept/path caused drift or unsafe reasoning. | `PruningRecord` scaffold and reports. | `scaffold only` | Feedback could become noisy if treated as truth. | stable failure taxonomy, lane permissions. | append-only feedback records, never direct deletion. | yes | no |
| episodic capture | Capture raw experiences/interactions before consolidation. | experiment stores and reports, no runtime interaction capture. | `partially implemented` | Capturing live user data without policy or retention rules. | output trace schema, privacy/scope policy, replay queue. | inert episode envelope first, user-approved capture later. | yes | yes |
| episodic-to-semantic consolidation | Convert episodes into reusable candidate concepts. | learning pipeline and Phase governance reports. | `partially implemented` | Reintroducing extraction/consolidation defects into live memory. | CandidateEnvelope, replay, canonical store. | batch consolidation into candidates only, not canonical writes. | yes | no |
| live canonical store | Durable trusted knowledge used by runtime. | candidate stores and isolated experiment stores only. | `absent` | Premature schema freeze and hard-to-reverse writes. | runtime metadata needs, provenance, rollback. | Candidate Canonical release first, canonical v1 after runtime needs are known. | yes | yes |
| CandidateEnvelope lifecycle | Track candidate state, confidence, provenance, and decisions. | `orchestration/runtime/v14_candidate_envelope.py`. | `scaffold only` | Low; inert schema only. | integration with replay/governance. | keep as the boundary object for future controlled learning. | yes | no |
| structural semantic adapter | Convert loose concepts into structured roles/signals. | `v14_signals.py` evidence-role metadata. | `scaffold only` | Poor labels could create false precision. | signal audit against V1.3 misses. | report-only signal tagging before active use. | yes | no |
| evidence role metadata | Represent why evidence matters. | `EvidenceRoleMetadata` scaffold. | `scaffold only` | Overconfident role labels could admit same-topic noise. | role assignment validation. | start as optional metadata and audit precision. | yes | no |
| lane-specific memory permissions | Control whether a concept can be used for activation, reasoning, planning, or response. | `v14_lanes.py`. | `scaffold only` | Accidental active blocks could hide useful concepts. | policy provenance, tests. | projection-only policies until a live store exists. | yes | no |
| hypothesis arbitration | Compare competing claims and decide which is better supported. | conflict handling and contradiction reports only. | `absent` | Could become another opaque scoring layer. | evidence roles, contradiction direction, confidence history. | report-only hypothesis packets first. | yes | yes |
| confidence inertia / volatility | Prevent confidence from oscillating too easily and track instability. | confidence metrics in reports, no runtime inertia state. | `absent` | Could hide real degradation if over-smoothed. | confidence trajectory data. | observational volatility reports before active inertia. | yes | yes |
| DMSA / multi-stream assessment | Independent streams assess evidence, safety, planning, and uncertainty. | sequential evaluation reports, no parallel assessment object. | `absent` | Can bloat architecture if made too heavy. | stable evaluator roles and veto policy. | lightweight report-only multi-check scorecard first. | maybe | yes |
| execution authorization / AEM-style gate | Prevent unsafe action or tool execution without explicit authorization. | invariants and output abstention scaffolds. | `partially implemented` | Very high risk if tool/action execution appears before gate. | calibrated output, action taxonomy, authorization ledger. | explicit authorization packet before any action-capable runtime. | yes | yes |
| unknown-answer port | Safely say "I do not know" and route/abstain without hallucination. | `v14_output_discipline.py`. | `scaffold only` | Low; currently inert. | response generator integration. | integrate before any live specialist routing or training. | yes | no |
| specialist SLM routing | Ask a domain specialist when governed knowledge is insufficient. | `v14_specialist_router.py` dormant route object. | `scaffold only` | Provider calls could bypass governance. | unknown-answer port, provider authorization, merge rules. | no-provider route object first; provider calls later behind gate. | yes | yes |
| controlled training | Learn from selected episodes/corrections under governance. | isolated campaigns only. | `absent` | Could contaminate candidate/canonical memory. | replay queue, candidate envelopes, negative feedback, live store. | disabled until explain, route, record, and reverse are implemented. | yes | yes |
| autonomous knowledge acquisition | System seeks new information without user prompt. | none. | `absent` | Broad safety and quality risk. | mature runtime, authorization, source policy, canonical rollback. | defer beyond V1.4; require explicit user policy. | maybe | yes |

## 6. Concepts To Preserve Directly

- CandidateEnvelope lifecycle
- evidence role metadata
- lane-specific memory permissions
- negative feedback records
- reversible pruning/dampening records
- unknown-answer output port
- dormant specialist route object

These already match the desired architecture as safe scaffolds. They should stay
inert until later phases intentionally wire them into runtime or learning.

## 7. Concepts To Preserve Functionally But Reimplement Differently

- Sleep should become scheduled replay/consolidation, not a literal special
  cognitive mode.
- Live pruning should become reversible lane-scoped dampening, not deletion.
- Canonical pruning should become governed demotion with rollback, not direct
  removal.
- Specialist routing should begin as a route request and merge envelope, not a
  provider call.
- DMSA should begin as a lightweight multi-check report, not a large new region.
- Controlled training should operate on CandidateEnvelope and replay records,
  not raw provider output.

## 8. Concepts That Must Wait

- live canonical store
- canonical pruning
- replay-driven memory mutation
- controlled training
- autonomous knowledge acquisition
- specialist provider calls
- action/execution authorization beyond abstention scaffolds

These should wait because DELTA cannot yet explain, route, record, and reverse
everything it learns or does.

## 9. Concepts That Are Risky Or Ambiguous

- literal sleep cycle versus scheduled replay
- live pruning versus reversible dampening
- canonical store timing
- DMSA scope
- specialist SLM routing scope
- execution authorization boundary
- autonomous acquisition policy

These are the places where the user's intended DELTA vision needs to drive the
next implementation choices.

## 10. Recommended Next Implementation Phase

Do not start training or live pruning yet.

Recommended next phase:

`Runtime V1.4C - Architecture Decision Lock`

The phase should resolve the user-decision points below, then choose one safe
path:

1. output discipline integration, if the priority is safer answers;
2. replay/sleep design, if the priority is preparing learning;
3. live store design, if the priority is canonical memory;
4. specialist routing design, if the priority is answering unknowns.

## 11. User Decision Points

1. Should sleep mean scheduled batch replay only, or should it eventually become
   a distinct runtime mode?
2. Should live pruning ever delete knowledge, or should all early pruning be
   reversible dampening?
3. Should canonical memory be designed before or after first output-discipline
   integration tests?
4. Should specialist SLM routing be allowed before canonical memory exists?
5. Should DMSA be a lightweight evaluator scorecard or a separate major
   subsystem?
6. What is the boundary between "answering" and "acting" for the AEM-style gate?
7. Should autonomous knowledge acquisition be a near-term roadmap item or a
   later policy-driven capability?

## 12. Continuation Checkpoint

- `runtime_v13_complete`: `True`
- `model_b_default_remains_active`: `True`
- `hyb1_dormant_only`: `True`
- `v14a_safe_scaffold_complete`: `True`
- `v14b_output_discipline_scaffold_complete`: `True`
- `training_enabled`: `False`
- `live_pruning_enabled`: `False`
- `canonical_writes_enabled`: `False`
- `provider_calls_enabled_by_specialist_router`: `False`
- `next_step`: `REQUEST_USER_ARCHITECTURE_DECISIONS`

REQUEST_USER_ARCHITECTURE_DECISIONS
